from .database import SessionLocal, Base, engine   # ✅ Added dot
from .models import Branch                        # ✅ Added dot

# Create tables
Base.metadata.create_all(bind=engine)

branches = [
    "Kilpauk","Mylapore","Velachery","Cuddalore","Tambaram","Mogappair",
    "Thoraipakkam","Avadi","Keelkattalai","Mugalivakkam","Sholinganallur",
    "Neelankarai","Kolathur","Pallikaranai","Old Perungalathur","Guduvanchery",
    "Puduchery","Ramapuram","Saidapet","Old Pallavaram","Mannivakkam",
    "Chidambaram","Hasthinapuram","Thiruverkadu","Surapet","Maraimalai Nagar",
    "Padur","Medavakkam","Ambattur","Arumbakkam","Ayapakkam","Sithalapakkam",
    "Perumbakkam","Basavanagudi","Pudupakkam","Urapakkam","Thanjavur","Pammal",
    "Kumbakonam","Maduravoyal","Kandigai","Kundrathur","Madambakkam","Navalur",
    "Kelambakkam","Iyyapanthangal","Mappedu"
]

db = SessionLocal()
for i, name in enumerate(branches):
    if not db.query(Branch).filter(Branch.name == name).first():
        db.add(Branch(name=name, access_code=f"F{i+1:02d}"))
db.commit()
db.close()

print(f"✅ Seeded {len(branches)} branches successfully!")