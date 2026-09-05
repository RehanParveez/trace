import asyncio
from uuid import uuid4, UUID
from datetime import date
import app.main
from app.core.database import AsyncSessionLocal
from app.modules.whatsapp.models import SitePhoto

ORG_A_ID = UUID("968010f3-bebc-4402-8b3d-4acfc4978fa9")

async def main():
    async with AsyncSessionLocal() as session:
        photo = SitePhoto(
            id=uuid4(),
            organization_id=ORG_A_ID,
            storage_key="dev/test-photo.jpg",
            sender_phone_number="923006208750",
            caption_raw="Foundation pour today at Gulberg site",
            photo_date=date.today(),
        )
        session.add(photo)
        await session.commit()
        print("Created SitePhoto:")
        print("  id:", photo.id)
        print("  organization_id:", photo.organization_id)

asyncio.run(main())