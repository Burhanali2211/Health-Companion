import json
import os

FILE_PATH = r"F:\watan-sehat\backend\data\diet_plans.json"

IMAGE_MAP = {
    "kahwa": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?auto=format&fit=crop&q=80&w=800",
    "tea": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?auto=format&fit=crop&q=80&w=800",
    "kheer": "https://images.unsplash.com/photo-1512485800893-b08ec1ea59b1?auto=format&fit=crop&q=80&w=800",
    "walnut": "https://images.unsplash.com/photo-1572358826727-b50106a735c0?auto=format&fit=crop&q=80&w=800",
    "harissa": "https://images.unsplash.com/photo-1544025162-8111142154ea?auto=format&fit=crop&q=80&w=800",
    "rogan josh": "https://images.unsplash.com/photo-1544025162-8111142154ea?auto=format&fit=crop&q=80&w=800",
    "roti": "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&q=80&w=800",
    "yakhni": "https://images.unsplash.com/photo-1548943487-a2e4b43b6852?auto=format&fit=crop&q=80&w=800",
    "bean": "https://images.unsplash.com/photo-1548943487-a2e4b43b6852?auto=format&fit=crop&q=80&w=800",
    "dal": "https://images.unsplash.com/photo-1548943487-a2e4b43b6852?auto=format&fit=crop&q=80&w=800",
    "saffron": "https://images.unsplash.com/photo-1620015525531-bc6a0bc98910?auto=format&fit=crop&q=80&w=800",
    "almond": "https://images.unsplash.com/photo-1508061253366-f7da158b6d46?auto=format&fit=crop&q=80&w=800",
    "chicken": "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?auto=format&fit=crop&q=80&w=800",
    "ginger": "https://images.unsplash.com/photo-1596541604605-720d750ecad3?auto=format&fit=crop&q=80&w=800",
    "garlic": "https://images.unsplash.com/photo-1596541604605-720d750ecad3?auto=format&fit=crop&q=80&w=800",
    "tulsi": "https://images.unsplash.com/photo-1596541604605-720d750ecad3?auto=format&fit=crop&q=80&w=800",
    "default": "https://images.unsplash.com/photo-1414235077428-3389886f6220?auto=format&fit=crop&q=80&w=800",
    "avoid_water": "https://images.unsplash.com/photo-1523362628745-0c100150b504?auto=format&fit=crop&q=80&w=800",
    "avoid_fruit": "https://images.unsplash.com/photo-1481134267576-90c74eb7fc06?auto=format&fit=crop&q=80&w=800",
    "avoid_drink": "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?auto=format&fit=crop&q=80&w=800"
}

def get_image_url(name_en, is_avoid=False):
    name_lower = name_en.lower()
    
    if is_avoid:
        if "water" in name_lower: return IMAGE_MAP["avoid_water"]
        if "fruit" in name_lower: return IMAGE_MAP["avoid_fruit"]
        if "drink" in name_lower: return IMAGE_MAP["avoid_drink"]
        return "https://images.unsplash.com/photo-1584288003444-4cd0f47e090b?auto=format&fit=crop&q=80&w=800"
        
    for key, url in IMAGE_MAP.items():
        if key in name_lower:
            return url
    return IMAGE_MAP["default"]

def update_dict(data):
    for season, age_groups in data.items():
        for age_group, meal_types in age_groups.items():
            for meal_type, items in meal_types.items():
                is_avoid = (meal_type == "avoid")
                for item in items:
                    if "name_en" in item:
                        item["image_url"] = get_image_url(item["name_en"], is_avoid)

def main():
    if not os.path.exists(FILE_PATH):
        print(f"File not found: {FILE_PATH}")
        return

    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    update_dict(data)

    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Successfully added image URLs to diet_plans.json")

if __name__ == "__main__":
    main()
