import json
import random

# A collection of beautiful, soft, minimalist aesthetic images from Unsplash
indoor_images = [
    'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?auto=format&fit=crop&q=80&w=800',
    'https://images.unsplash.com/photo-1599901860904-17e08c3d0cb7?auto=format&fit=crop&q=80&w=800',
    'https://images.unsplash.com/photo-1518609878373-06d740f60d8b?auto=format&fit=crop&q=80&w=800',
    'https://images.unsplash.com/photo-1552822987-a0201389e9f6?auto=format&fit=crop&q=80&w=800'
]

outdoor_images = [
    'https://images.unsplash.com/photo-1552674605-17147cea8732?auto=format&fit=crop&q=80&w=800',
    'https://images.unsplash.com/photo-1538805060514-97d9cc17730c?auto=format&fit=crop&q=80&w=800',
    'https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?auto=format&fit=crop&q=80&w=800',
    'https://images.unsplash.com/photo-1502086223501-7ea6ecd79368?auto=format&fit=crop&q=80&w=800'
]

breathing_images = [
    'https://images.unsplash.com/photo-1499209974431-9dddcece7f88?auto=format&fit=crop&q=80&w=800',
    'https://images.unsplash.com/photo-1508672019048-805c876b67e2?auto=format&fit=crop&q=80&w=800',
    'https://images.unsplash.com/photo-1515023115689-589c33041d3c?auto=format&fit=crop&q=80&w=800',
    'https://images.unsplash.com/photo-1447452001602-7090c7ab2db3?auto=format&fit=crop&q=80&w=800'
]

morning_images = [
    'https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&q=80&w=800',
    'https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?auto=format&fit=crop&q=80&w=800',
    'https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&q=80&w=800',
    'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&q=80&w=800'
]

images_map = {
    'indoor': indoor_images,
    'outdoor': outdoor_images,
    'breathing': breathing_images,
    'morning': morning_images
}

# Diverse titles for dummy data
titles_map = {
    'indoor': ["Warm Room Yoga", "Gentle Pilates Flow", "Indoor Core Strength", "Soft Body Stretching", "Living Room Cardio", "Cozy Corner Meditation"],
    'outdoor': ["Brisk Morning Walk", "Light Jogging", "Park Bench Stretches", "Nature Trail Hike", "Outdoor Mobility Drill", "Sunshine Aerobics"],
    'breathing': ["Deep Belly Breathing", "Box Breathing Technique", "Alternate Nostril Rhythm", "Calm Mind Inhales", "Soothing Exhalations", "Ocean Sound Breath"],
    'morning': ["Sunrise Sun Salutation", "Bedside Stretching", "Morning Joint Mobility", "Energizing Flow", "Wake-up Yoga", "Gentle Morning Awakening"]
}

def process():
    file_path = 'exercises.json'
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    def make_dummy(cat, i):
        title = random.choice(titles_map[cat])
        img = random.choice(images_map[cat])
        return {
            "id": f"dummy_{cat}_{i}_{random.randint(1000,9999)}",
            "name_en": title,
            "duration_min": random.choice([5, 10, 15, 20]),
            "sets": random.choice([2, 3, 4]),
            "reps": random.choice([8, 10, 12, 15]),
            "science": f"A carefully curated {cat} exercise to promote relaxation and strength.",
            "image_url": img
        }
    
    for season, ages in data.items():
        if season == "season_locks":
            continue
        for age, categories in ages.items():
            for cat in ['indoor', 'outdoor', 'breathing', 'morning']:
                if cat not in categories or categories[cat] is None:
                    categories[cat] = []
                
                # If there are existing items with same image, remove them or update them to be diverse
                # We will just ensure there are at least 5 varied items
                # Let's clear the old dummies we just made
                categories[cat] = [ex for ex in categories[cat] if not str(ex.get('id', '')).startswith('dummy_')]
                
                # ensure there are at least 5 items
                i = 0
                while len(categories[cat]) < 6:
                    categories[cat].append(make_dummy(cat, i))
                    i += 1
                
                # add diverse images to existing real data
                for ex in categories[cat]:
                    if not ex.get('image_url') or ex.get('image_url') == images_map[cat][0]:
                        ex['image_url'] = random.choice(images_map[cat])
                    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    process()
    print("Done generating rich data.")
