from __future__ import annotations
import asyncio
from uuid import uuid4
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.modules.whatsapp.permissions import WHATSAPP_PERMISSIONS
from uuid import UUID, uuid4
from app.modules.whatsapp.models import WhatsAppChannel
from app.shared.seed_utils import seed_module_permissions
from app.modules.whatsapp.permissions import WHATSAPP_PERMISSIONS
 
DEFAULT_ROLE_NAME = "Company Admin"

NATIONAL_PROJECT_MANAGEMENT_ORG_ID = UUID(
  "bf47e815-0147-43a9-82b4-1d3d224f17b9"
)
 
async def seed_whatsapp() -> None:
  async with AsyncSessionLocal() as session:
    await seed_module_permissions(session, WHATSAPP_PERMISSIONS)
    
    channel_result = await session.execute(
      select(WhatsAppChannel).where(WhatsAppChannel.organization_id
        == NATIONAL_PROJECT_MANAGEMENT_ORG_ID
      )
    )
    channel = channel_result.scalar_one_or_none()

    if channel is None:
      channel = WhatsAppChannel(id=uuid4(), organization_id=NATIONAL_PROJECT_MANAGEMENT_ORG_ID, phone_number_id="dev-phone-number-id", business_account_id="dev-business-account-id",
        display_phone_number="+92 300 6208750", access_token="dev-access-token", is_active=True,
      )
      session.add(channel)
      await session.commit()

      print("WhatsApp development channel created.")
      print(f"Channel ID: {channel.id}")
      print(f"Organization ID: {channel.organization_id}")
      print(f"Phone Number ID: {channel.phone_number_id}")
    else:
      print("WhatsApp channel already exists.")
      print(f"Channel ID: {channel.id}")
      print(f"Organization ID: {channel.organization_id}")
      print(f"Phone Number ID: {channel.phone_number_id}")
 
if __name__ == "__main__":
  asyncio.run(seed_whatsapp())