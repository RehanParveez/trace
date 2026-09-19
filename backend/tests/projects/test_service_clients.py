from __future__ import annotations
from uuid import uuid4
import pytest
from app.core.exceptions import TraceException
from app.modules.projects.schemas import ClientCreate, ClientUpdate

@pytest.mark.asyncio
class TestClientService:
  async def test_create_client_success(self, project_service, organization):
    payload = ClientCreate(
      name="Trace Construction",
      contact_name="Aayan Raees",
      email="aayan@trace.com",
      phone="+92-3126208750",
      address="4 Main St",
      notes="Preferred client",
    )
    client = await project_service.create_client(organization.id, payload)

    assert client.id is not None
    assert client.organization_id == organization.id
    assert client.name == "Trace Construction"
    assert client.contact_name == "Aayan Raees"
    assert client.email == "aayan@trace.com"
    assert client.phone == "+92-3126208750"
    assert client.address == "4 Main St"
    assert client.notes == "Preferred client"

  async def test_create_client_duplicate_name_case_insensitive(
    self,
    project_service,
    organization,
    client_factory,
  ):
    await client_factory(name="Trace Construction")

    payload = ClientCreate(name="trace construction")
    with pytest.raises(TraceException) as exc:
      await project_service.create_client(organization.id, payload)
    assert exc.value.status_code == 409
    assert exc.value.code == "CLIENT_ALREADY_EXISTS"

  async def test_list_clients_scoped_to_organization(
    self,
    project_service,
    organization,
    client_factory,
    other_organization,
  ):
    c1 = await client_factory(name="Client A")
    c2 = await client_factory(name="Client B")
    await client_factory(organization_id=other_organization.id, name="Other Org Client")

    clients = await project_service.list_clients(organization.id)
    names = {c.name for c in clients}
    assert "Client A" in names
    assert "Client B" in names
    assert "Other Org Client" not in names
    assert all(c.organization_id == organization.id for c in clients)

  async def test_get_client_success_and_not_found(
    self,
    project_service,
    organization,
    client_factory,
  ):
    client = await client_factory()
    found = await project_service.get_client(organization.id, client.id)
    assert found.id == client.id

    with pytest.raises(TraceException) as exc:
      await project_service.get_client(organization.id, uuid4())
    assert exc.value.status_code == 404
    assert exc.value.code == "CLIENT_NOT_FOUND"

    with pytest.raises(TraceException) as exc:
      await project_service.get_client(uuid4(), client.id)
    assert exc.value.code == "CLIENT_NOT_FOUND"

  async def test_update_client_partial_and_name_uniqueness(
    self,
    project_service,
    organization,
    client_factory,
  ):
    client = await client_factory(name="Original Name")
    other = await client_factory(name="Taken Name")

    updated = await project_service.update_client(
      organization.id,
      client.id,
      ClientUpdate(contact_name="New Contact", notes="Updated notes"),
    )
    assert updated.contact_name == "New Contact"
    assert updated.notes == "Updated notes"
    assert updated.name == "Original Name"

    updated = await project_service.update_client(
      organization.id,
      client.id,
      ClientUpdate(name="Brand New Name"),
    )
    assert updated.name == "Brand New Name"

    with pytest.raises(TraceException) as exc:
      await project_service.update_client(
        organization.id,
        client.id,
        ClientUpdate(name="Taken Name"),
      )
    assert exc.value.code == "CLIENT_ALREADY_EXISTS"

    updated = await project_service.update_client(
      organization.id,
      client.id,
      ClientUpdate(name="Brand New Name"),
    )
    assert updated.name == "Brand New Name"

  async def test_delete_client_blocked_when_linked_to_projects(
    self,
    project_service,
    organization,
    client_factory,
    project_factory,
  ):
    client = await client_factory()
    await project_factory(client=client)

    with pytest.raises(TraceException) as exc:
      await project_service.delete_client(organization.id, client.id)
    assert exc.value.status_code == 409
    assert exc.value.code == "CLIENT_HAS_PROJECTS"

  async def test_delete_client_success_when_unlinked(
    self,
    project_service,
    organization,
    client_factory,
  ):
    client = await client_factory()
    await project_service.delete_client(organization.id, client.id)

    with pytest.raises(TraceException) as exc:
      await project_service.get_client(organization.id, client.id)
    assert exc.value.code == "CLIENT_NOT_FOUND"