from app import db
from bson import ObjectId

class Professional:
    def __init__(self, name, specialization, bio, qualifications, availability, location):
        self.name = name
        self.specialization = specialization
        self.bio = bio
        self.qualifications = qualifications
        self.availability = availability
        self.location = location

    def save(self):
        professional_data = {
            'name': self.name,
            'specialization': self.specialization,
            'bio': self.bio,
            'qualifications': self.qualifications,
            'availability': self.availability,
            'location': self.location
        }
        result = db.professionals.insert_one(professional_data)
        self.id = str(result.inserted_id)
        return self.id

    @staticmethod
    def get_by_id(professional_id):
        professional_data = db.professionals.find_one({'_id': ObjectId(professional_id)})
        if professional_data:
            professional = Professional(
                name=professional_data['name'],
                specialization=professional_data['specialization'],
                bio=professional_data['bio'],
                qualifications=professional_data['qualifications'],
                availability=professional_data['availability'],
                location=professional_data['location']
            )
            professional.id = str(professional_data['_id'])
            return professional
        return None

    @staticmethod
    def get_all():
        professionals = []
        cursor = db.professionals.find()
        
        for professional_data in cursor:
            professional = Professional(
                name=professional_data['name'],
                specialization=professional_data['specialization'],
                bio=professional_data['bio'],
                qualifications=professional_data['qualifications'],
                availability=professional_data['availability'],
                location=professional_data['location']
            )
            professional.id = str(professional_data['_id'])
            professionals.append(professional)
        
        return professionals 