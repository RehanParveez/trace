import asyncio
import io
from uuid import uuid4, UUID
from datetime import date
from app.core.database import AsyncSessionLocal
from app.modules.identity.models import Organization, User
from app.modules.projects.models import Client, Project, ProjectMember, Milestone
from app.modules.whatsapp.models import SitePhoto

from app.shared.storage import build_site_photo_storage_key, upload_fileobj

ORG_ID = UUID("968010f3-bebc-4402-8b3d-4acfc4978fa9")
LOCAL_IMAGE_PATH = "/tmp/test-site-photo.jpg"

async def main():
    with open(LOCAL_IMAGE_PATH, "rb") as f:
        contents = f.read()

    storage_key = build_site_photo_storage_key(ORG_ID, "test-site-photo.jpg")
    upload_fileobj(storage_key, io.BytesIO(contents), "image/jpeg")

    async with AsyncSessionLocal() as session:
        photo = SitePhoto(
            id=uuid4(),
            organization_id=ORG_ID,
            storage_key=storage_key,
            sender_phone_number="923006208750",
            caption_raw="Concrete slab test photo",
            photo_date=date.today(),
        )
        session.add(photo)
        await session.commit()
        print("Created SitePhoto:", photo.id)

asyncio.run(main())