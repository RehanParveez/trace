import asyncio
import base64
from io import BytesIO
from uuid import uuid4, UUID
from datetime import date
import app.main
from app.core.database import AsyncSessionLocal
from app.modules.whatsapp.models import SitePhoto
from app.shared.storage import ensure_bucket, upload_fileobj

ORG_A_ID = UUID("f14b7835-f091-4300-9b21-9445cf329924")

PLACEHOLDER_JPEG = base64.b64decode(
  "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAA0JCgsKCA0LCgsODg0PEyAVExISEyccHhcgLikxMC4pLSwzOko+MzZGNy"
  "wtQFdBRkxOUlNSMj5aYVpQYEpRUk//2wBDAQ4ODhMREyYVFSZPNS01T09PT09PT09PT09PT09PT09PT09PT09PT09P"
  "T09PT09PT09PT09PT09PT09PT09PT0//wAARCAAwAEADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAw"
  "QFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkK"
  "FhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmq"
  "KjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEB"
  "AQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRob"
  "HBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOE"
  "hYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+P"
  "n6/9oADAMBAAIRAxEAPwCaiiitjAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigD//Z"
)

async def main():
  ensure_bucket()
  storage_key = f"{ORG_A_ID}/site-photos/unassigned/seed-test-photo.jpg"
  upload_fileobj(storage_key, BytesIO(PLACEHOLDER_JPEG), "image/jpeg")
  async with AsyncSessionLocal() as session:
    photo = SitePhoto(
      id=uuid4(),
      organization_id=ORG_A_ID,
      storage_key=storage_key,
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