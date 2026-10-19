from __future__ import annotations
import asyncio
import base64
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import Text, text
from sqlalchemy.types import TypeDecorator
from app.core.config import settings

logger = logging.getLogger("trace.crypto")

TOKEN_PREFIX = "enc:v1:"
_NONCE_BYTES = 12

class CryptoError(RuntimeError):
  """Encryption or decryption could not be done. The data is never returned or stored in the clear when this is raised."""

def is_encrypted(value: str | None) -> bool:
  return isinstance(value, str) and value.startswith(TOKEN_PREFIX)

class KeyProvider(Protocol):
  name: str

  def new_data_key(self, org_id: UUID) -> tuple[bytes, bytes, str]:
    """Return (plain data key, wrapped data key, key reference)."""

  def unwrap(self, org_id: UUID, wrapped: bytes, key_ref: str) -> bytes:
    ...

class LocalKeyProvider:

  name = "local"

  def __init__(self, master_key_b64: str):
    try:
      key = base64.b64decode(master_key_b64, validate=True)
    except Exception as exc:  
      raise CryptoError("ENCRYPTION_MASTER_KEY is not valid base64.") from exc
    if len(key) != 32:
      raise CryptoError("ENCRYPTION_MASTER_KEY must decode to exactly 32 bytes.")
    self._aead = AESGCM(key)

  def new_data_key(self, org_id: UUID) -> tuple[bytes, bytes, str]:
    dek = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(_NONCE_BYTES)
    wrapped = nonce + self._aead.encrypt(nonce, dek, f"dek:{org_id}".encode())
    return dek, wrapped, "local"

  def unwrap(self, org_id: UUID, wrapped: bytes, key_ref: str) -> bytes:
    nonce, body = wrapped[:_NONCE_BYTES], wrapped[_NONCE_BYTES:]
    try:
      return self._aead.decrypt(nonce, body, f"dek:{org_id}".encode())
    except Exception as exc:  
      raise CryptoError("The data key of this organization cannot be unwrapped with the configured master key.") from exc

class AwsKmsKeyProvider:
  name = "aws_kms"

  def __init__(self, key_id: str, region: str = ""):
    if not key_id:
      raise CryptoError("ENCRYPTION_KMS_KEY_ID is required for the aws_kms provider.")
    self._key_id = key_id
    self._region = region or None
    self._client = None

  def _kms(self):
    if self._client is None:
      import boto3

      self._client = boto3.client("kms", region_name=self._region)
    return self._client

  def new_data_key(self, org_id: UUID) -> tuple[bytes, bytes, str]:
    out = self._kms().generate_data_key(KeyId=self._key_id, KeySpec="AES_256", EncryptionContext={"organization_id": str(org_id)})
    return out["Plaintext"], out["CiphertextBlob"], self._key_id

  def unwrap(self, org_id: UUID, wrapped: bytes, key_ref: str) -> bytes:
    out = self._kms().decrypt(CiphertextBlob=wrapped, KeyId=key_ref or self._key_id, EncryptionContext={"organization_id": str(org_id)})
    return out["Plaintext"]

def build_provider(name: str) -> KeyProvider:
  if name == "local":
    return LocalKeyProvider(settings.encryption_master_key)
  if name == "aws_kms":
    return AwsKmsKeyProvider(settings.encryption_kms_key_id, settings.encryption_kms_region)
  raise CryptoError(f"Unknown encryption provider: {name!r}.")

@dataclass
class _OrgKeys:
  versions: dict[int, bytes]
  current: int
  expires: float = field(default=0.0)

class KeyRing:
  """Process-wide cache of the data keys of the organizations this process works for."""

  def __init__(self) -> None:
    self._cache: dict[UUID, _OrgKeys] = {}
    self._providers: dict[str, KeyProvider] = {}
    self.create_in_session = False
    self.session_factory = None

  @property
  def provider_name(self) -> str:
    return (settings.encryption_provider or "none").lower()

  @property
  def enabled(self) -> bool:
    return self.provider_name != "none"

  def _provider(self, name: str) -> KeyProvider:
    provider = self._providers.get(name)
    if provider is None:
      provider = build_provider(name)
      self._providers[name] = provider
    return provider

  def reset(self) -> None:
    self._cache.clear()
    self._providers.clear()

  def forget(self, org_id: UUID) -> None:
    self._cache.pop(org_id, None)

  def install(self, org_id: UUID, versions: dict[int, bytes], current: int) -> None:
    self._cache[org_id] = _OrgKeys(dict(versions), current, time.monotonic() + max(int(settings.encryption_dek_cache_seconds), 1))

  def _live(self, org_id: UUID) -> _OrgKeys | None:
    keys = self._cache.get(org_id)
    if keys is None:
      return None
    if keys.expires < time.monotonic():
      self._cache.pop(org_id, None)
      return None
    return keys

  def has_key(self, org_id: UUID) -> bool:
    return self._live(org_id) is not None

  async def ensure_loaded(self, session, org_id: UUID) -> None:
    if not self.enabled or self._live(org_id) is not None:
      return
    from app.modules.privacy.models import OrganizationKey
    from sqlalchemy import select

    rows = (await session.execute(
      select(OrganizationKey).where(OrganizationKey.organization_id == org_id).order_by(OrganizationKey.version)
    )).scalars().all()
    if not rows:
      rows = [await self._create_first_key(session, org_id)]
    versions: dict[int, bytes] = {}
    current = 0
    
    for row in rows:
      provider = self._provider(row.provider)
      versions[row.version] = await asyncio.to_thread(provider.unwrap, org_id, bytes(row.wrapped_dek), row.key_ref or "")
      if row.is_current:
        current = row.version
    if not current:
      current = max(versions)
    self.install(org_id, versions, current)

  async def _create_first_key(self, session, org_id: UUID):
    from app.modules.privacy.models import OrganizationKey
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError

    provider = self._provider(self.provider_name)
    dek, wrapped, ref = await asyncio.to_thread(provider.new_data_key, org_id)
    row = OrganizationKey(organization_id=org_id, version=1, wrapped_dek=wrapped, provider=provider.name, key_ref=ref, is_current=True)
    if self.create_in_session:
      session.add(row)
      await session.flush()
      return row
    factory = self.session_factory or _default_session_factory(session)
    try:
      async with factory() as own:
        await own.execute(text("SELECT set_config('app.current_org_id', :o, true)"), {"o": str(org_id)})
        own.add(row)
        await own.commit()
    except IntegrityError:

      async with factory() as own:
        await own.execute(text("SELECT set_config('app.current_org_id', :o, true)"), {"o": str(org_id)})
        found = (await own.execute(select(OrganizationKey).where(OrganizationKey.organization_id == org_id).order_by(OrganizationKey.version))).scalars().first()
        if found is None:
          raise
        return found
    return row

  def _keys_for(self, org_id: UUID) -> _OrgKeys:
    keys = self._live(org_id)
    if keys is None:
      raise CryptoError("The encryption key of this organization is not loaded. Scope the session to the organization first.")
    return keys

  def encrypt(self, org_id: UUID, label: str, plaintext: str) -> str:
    keys = self._keys_for(org_id)
    nonce = os.urandom(_NONCE_BYTES)
    sealed = AESGCM(keys.versions[keys.current]).encrypt(nonce, plaintext.encode("utf-8"), f"{org_id}:{label}".encode())
    return f"{TOKEN_PREFIX}{org_id}:{keys.current}:{base64.urlsafe_b64encode(nonce + sealed).decode()}"

  def decrypt(self, label: str, token: str) -> str:
    try:
      org_s, ver_s, blob = token[len(TOKEN_PREFIX):].split(":", 2)
      org_id, version = UUID(org_s), int(ver_s)
      raw = base64.urlsafe_b64decode(blob.encode())
    except Exception as exc:  
      raise CryptoError("The stored value is not a valid encrypted value.") from exc
    keys = self._keys_for(org_id)
    dek = keys.versions.get(version)
    if dek is None:
      raise CryptoError(f"Data key version {version} of this organization is not available.")
    try:
      return AESGCM(dek).decrypt(raw[:_NONCE_BYTES], raw[_NONCE_BYTES:], f"{org_id}:{label}".encode()).decode("utf-8")
    except Exception as exc:  
      raise CryptoError("The stored value could not be decrypted (wrong key, wrong column or altered data).") from exc

def _default_session_factory(session):
  from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
  from sqlalchemy.ext.asyncio import AsyncEngine

  bind = session.bind
  if hasattr(bind, "sync_connection"):  
    bind = bind.engine
  if not isinstance(bind, AsyncEngine):  
    bind = AsyncEngine(getattr(bind, "engine", bind))
  return async_sessionmaker(bind=bind, class_=AsyncSession, expire_on_commit=False)

keyring = KeyRing()

def _current_org() -> UUID:
  from app.dependencies.tenancy import _current_organization_id
  org = _current_organization_id.get()
  if org is None:
    raise CryptoError("An encrypted column was written outside an organization scope.")
  return org

def seal(label: str, plaintext: str) -> str:
  if not keyring.enabled:
    return plaintext
  return keyring.encrypt(_current_org(), label, plaintext)

def open_(label: str, stored: str) -> str:
  if not is_encrypted(stored):
    return stored
  return keyring.decrypt(label, stored)

class EncryptedText(TypeDecorator):
  """A TEXT column whose value is sealed with the key of the organization in scope."""

  impl = Text
  cache_ok = True

  def __init__(self, label: str):
    super().__init__()
    self.label = label

  def process_bind_param(self, value: Any, dialect) -> str | None:
    return None if value is None else seal(self.label, value)

  def process_result_value(self, value: Any, dialect) -> str | None:
    return None if value is None else open_(self.label, value)

class EncryptedJSON(TypeDecorator):
  """A JSON value kept in a TEXT column, sealed with the key of the organization in scope."""

  impl = Text
  cache_ok = True

  def __init__(self, label: str):
    super().__init__()
    self.label = label

  def process_bind_param(self, value: Any, dialect) -> str | None:
    return None if value is None else seal(self.label, json.dumps(value, default=str))

  def process_result_value(self, value: Any, dialect) -> Any:
    if value is None:
      return None
    plain = open_(self.label, value)
    try:
      return json.loads(plain)
    except ValueError:
      return plain

def check_settings() -> None:
  """Fail at startup, not at the first write, when the encryption settings are unusable."""
  name = (settings.encryption_provider or "none").lower()
  if name == "none":
    return
  if name == "local" and settings.app_env.lower() == "production":
    raise CryptoError("The local encryption provider keeps the master key in the environment and is not allowed in production. Use aws_kms.")
  build_provider(name)