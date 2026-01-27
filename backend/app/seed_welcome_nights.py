"""
Seed data for Welcome Nights Presentation Builder

Run with: python -m app.seed_welcome_nights
"""

from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from . import models

# Ensure tables exist
models.Base.metadata.create_all(bind=engine)


def seed_brands(db: Session):
    """Seed Cascadia and Olympus brands"""
    brands = [
        {
            "name": "Cascadia Healthcare",
            "slug": "cascadia",
            "primary_color": "#0b7280",
            "secondary_color": "#065a67",
            "font_family": "Inter",
        },
        {
            "name": "Olympus Retirement Living",
            "slug": "olympus",
            "primary_color": "#1e40af",
            "secondary_color": "#1e3a8a",
            "font_family": "Inter",
        },
    ]

    created = []
    for brand_data in brands:
        existing = db.query(models.Brand).filter(models.Brand.slug == brand_data["slug"]).first()
        if not existing:
            brand = models.Brand(**brand_data)
            db.add(brand)
            created.append(brand_data["name"])
    db.commit()
    return created


def seed_games(db: Session):
    """Seed default games library"""
    games = [
        # Ice Breaker
        {
            "brand_id": None,  # Global game
            "title": "Musical Chairs",
            "description": "Classic ice breaker game to get everyone moving and laughing",
            "rules": "1. Set up chairs in a circle (one less than players)\n2. Play music while players walk around chairs\n3. When music stops, everyone sits\n4. Player without a chair is out\n5. Remove one chair and repeat\n6. Last person seated wins!",
            "duration_minutes": 15,
            "min_players": 6,
            "max_players": 20,
            "game_type": "icebreaker",
            "value_label": "TEAMWORK",
            "tags": ["fun", "active", "classic"],
        },
        # Minute-to-Win-It Challenges
        {
            "brand_id": None,
            "title": "Cookie Face",
            "description": "Move a cookie from forehead to mouth using only facial muscles",
            "rules": "1. Place a cookie on your forehead\n2. Using only facial muscles, move the cookie to your mouth\n3. No hands allowed!\n4. You have 60 seconds\n5. First to eat the cookie wins!",
            "duration_minutes": 5,
            "min_players": 2,
            "max_players": 10,
            "game_type": "challenge",
            "value_label": "FAMILY",
            "tags": ["minute-to-win-it", "funny", "individual"],
        },
        {
            "brand_id": None,
            "title": "Cup Stacking",
            "description": "Stack and unstack cups in a pyramid as fast as possible",
            "rules": "1. Start with cups stacked together\n2. Build a pyramid (3-2-1 formation)\n3. Then collapse back to a single stack\n4. Fastest time wins!\n5. If pyramid falls, start over",
            "duration_minutes": 5,
            "min_players": 2,
            "max_players": 10,
            "game_type": "challenge",
            "value_label": "EXCELLENCE",
            "tags": ["minute-to-win-it", "speed", "dexterity"],
        },
        {
            "brand_id": None,
            "title": "Marshmallow Tower",
            "description": "Build the tallest tower using marshmallows and spaghetti",
            "rules": "1. Teams of 3-4 people\n2. Use spaghetti and marshmallows only\n3. Build the tallest freestanding tower\n4. Tower must stand for 10 seconds\n5. You have 5 minutes\n6. Tallest tower wins!",
            "duration_minutes": 7,
            "min_players": 6,
            "max_players": 20,
            "game_type": "challenge",
            "value_label": "INNOVATION",
            "tags": ["minute-to-win-it", "teamwork", "creative"],
        },
        {
            "brand_id": None,
            "title": "Pencil Flip",
            "description": "Flip a pencil from the back of your hand and catch it",
            "rules": "1. Balance a pencil on the back of your hand\n2. Flip your hand and catch the pencil\n3. Start with 1 pencil, add more each round\n4. Most pencils caught wins!\n5. Must catch all pencils in one motion",
            "duration_minutes": 5,
            "min_players": 2,
            "max_players": 10,
            "game_type": "challenge",
            "value_label": "OWNERSHIP",
            "tags": ["minute-to-win-it", "skill", "individual"],
        },
        {
            "brand_id": None,
            "title": "Flip Cup",
            "description": "Team relay race flipping cups",
            "rules": "1. Two teams line up on opposite sides of table\n2. First player drinks (water) and flips cup\n3. Cup must land upside down\n4. Next player goes when cup lands\n5. First team to finish wins!",
            "duration_minutes": 10,
            "min_players": 6,
            "max_players": 20,
            "game_type": "challenge",
            "value_label": "TEAMWORK",
            "tags": ["minute-to-win-it", "team", "relay"],
        },
    ]

    created = []
    for game_data in games:
        existing = db.query(models.Game).filter(models.Game.title == game_data["title"]).first()
        if not existing:
            game = models.Game(**game_data)
            db.add(game)
            created.append(game_data["title"])
    db.commit()
    return created


def seed_agenda_templates(db: Session):
    """Seed default agenda templates for each brand"""
    # Get brands
    cascadia = db.query(models.Brand).filter(models.Brand.slug == "cascadia").first()
    olympus = db.query(models.Brand).filter(models.Brand.slug == "olympus").first()

    if not cascadia or not olympus:
        return []

    default_slide_blocks = [
        {"type": "welcome_intro", "required": True},
        {"type": "icebreaker", "required": False},
        {"type": "history", "required": False},
        {"type": "footprint", "required": False},
        {"type": "regions", "required": False},
        {"type": "culture", "required": False},
        {"type": "challenges", "required": False},
        {"type": "pillars_closing", "required": True},
    ]

    templates = [
        # Cascadia templates
        {
            "brand_id": cascadia.id,
            "name": "Culture Night",
            "description": "Full culture night presentation with all content blocks and games",
            "default_config": {
                "raffle_count": 3,
                "include_history": True,
                "include_footprint": True,
                "include_regions": True,
                "include_culture": True,
            },
            "slide_blocks": default_slide_blocks,
            "raffle_breakpoints": [2, 4, 6],
        },
        {
            "brand_id": cascadia.id,
            "name": "Welcome Night",
            "description": "Shorter welcome night for new employees - focus on culture and values",
            "default_config": {
                "raffle_count": 1,
                "include_history": True,
                "include_footprint": False,
                "include_regions": False,
                "include_culture": True,
            },
            "slide_blocks": [
                {"type": "welcome_intro", "required": True},
                {"type": "icebreaker", "required": False},
                {"type": "history", "required": False},
                {"type": "culture", "required": False},
                {"type": "pillars_closing", "required": True},
            ],
            "raffle_breakpoints": [3],
        },
        # Olympus templates
        {
            "brand_id": olympus.id,
            "name": "Culture Night",
            "description": "Full Olympus culture night presentation",
            "default_config": {
                "raffle_count": 3,
                "include_history": True,
                "include_footprint": True,
                "include_regions": True,
                "include_culture": True,
            },
            "slide_blocks": default_slide_blocks,
            "raffle_breakpoints": [2, 4, 6],
        },
        {
            "brand_id": olympus.id,
            "name": "Welcome Night",
            "description": "Olympus welcome night for new team members",
            "default_config": {
                "raffle_count": 1,
                "include_history": True,
                "include_footprint": False,
                "include_regions": False,
                "include_culture": True,
            },
            "slide_blocks": [
                {"type": "welcome_intro", "required": True},
                {"type": "icebreaker", "required": False},
                {"type": "history", "required": False},
                {"type": "culture", "required": False},
                {"type": "pillars_closing", "required": True},
            ],
            "raffle_breakpoints": [3],
        },
    ]

    created = []
    for template_data in templates:
        existing = db.query(models.AgendaTemplate).filter(
            models.AgendaTemplate.brand_id == template_data["brand_id"],
            models.AgendaTemplate.name == template_data["name"]
        ).first()
        if not existing:
            template = models.AgendaTemplate(**template_data)
            db.add(template)
            created.append(f"{template_data['name']} ({template_data['brand_id']})")
    db.commit()
    return created


def seed_reusable_content(db: Session):
    """Seed default reusable content blocks for each brand"""
    cascadia = db.query(models.Brand).filter(models.Brand.slug == "cascadia").first()
    olympus = db.query(models.Brand).filter(models.Brand.slug == "olympus").first()

    if not cascadia or not olympus:
        return []

    content_items = [
        # Cascadia content
        {
            "brand_id": cascadia.id,
            "content_key": "history",
            "title": "Our History",
            "content": {
                "items": [
                    {"year": "2010", "text": "Cascadia Healthcare founded"},
                    {"year": "2015", "text": "Expanded to 10 facilities"},
                    {"year": "2020", "text": "Reached 50+ facilities across the Pacific Northwest"},
                    {"year": "Today", "text": "Continuing to grow with excellence in care"},
                ]
            },
        },
        {
            "brand_id": cascadia.id,
            "content_key": "footprint",
            "title": "Our Growing Footprint",
            "content": {
                "stats": [
                    {"label": "Facilities", "value": "50+"},
                    {"label": "Team Members", "value": "5,000+"},
                    {"label": "Residents Served", "value": "10,000+"},
                    {"label": "States", "value": "5"},
                ]
            },
        },
        {
            "brand_id": cascadia.id,
            "content_key": "regions",
            "title": "Our Regions",
            "content": {
                "regions": [
                    {"name": "Pacific Northwest", "facilities": 25},
                    {"name": "Mountain West", "facilities": 15},
                    {"name": "Southwest", "facilities": 10},
                ]
            },
        },
        {
            "brand_id": cascadia.id,
            "content_key": "culture",
            "title": "The Cascadia Way",
            "content": {
                "subtitle": "We are NOT corporate",
                "comparisons": [
                    {"cascadia": "Family-focused culture", "common": "Corporate bureaucracy"},
                    {"cascadia": "Local decision making", "common": "Top-down mandates"},
                    {"cascadia": "Invest in our people", "common": "Cost-cutting focus"},
                    {"cascadia": "Quality over quantity", "common": "Volume metrics"},
                ]
            },
        },
        # Olympus content
        {
            "brand_id": olympus.id,
            "content_key": "history",
            "title": "Our History",
            "content": {
                "items": [
                    {"year": "2012", "text": "Olympus Retirement Living established"},
                    {"year": "2017", "text": "First retirement community opened"},
                    {"year": "2022", "text": "Expanded to multiple states"},
                    {"year": "Today", "text": "Leading provider of retirement living"},
                ]
            },
        },
        {
            "brand_id": olympus.id,
            "content_key": "footprint",
            "title": "Our Growing Footprint",
            "content": {
                "stats": [
                    {"label": "Communities", "value": "25+"},
                    {"label": "Team Members", "value": "2,000+"},
                    {"label": "Residents", "value": "5,000+"},
                    {"label": "States", "value": "3"},
                ]
            },
        },
        {
            "brand_id": olympus.id,
            "content_key": "regions",
            "title": "Our Regions",
            "content": {
                "regions": [
                    {"name": "West Coast", "facilities": 15},
                    {"name": "Mountain Region", "facilities": 10},
                ]
            },
        },
        {
            "brand_id": olympus.id,
            "content_key": "culture",
            "title": "The Olympus Way",
            "content": {
                "subtitle": "Elevating Retirement Living",
                "comparisons": [
                    {"olympus": "Person-centered care", "common": "One-size-fits-all"},
                    {"olympus": "Empowered teams", "common": "Micromanagement"},
                    {"olympus": "Community partnerships", "common": "Isolation"},
                    {"olympus": "Continuous improvement", "common": "Status quo"},
                ]
            },
        },
    ]

    created = []
    for item_data in content_items:
        existing = db.query(models.ReusableContent).filter(
            models.ReusableContent.brand_id == item_data["brand_id"],
            models.ReusableContent.content_key == item_data["content_key"]
        ).first()
        if not existing:
            content = models.ReusableContent(**item_data)
            db.add(content)
            created.append(f"{item_data['content_key']} ({item_data['brand_id']})")
    db.commit()
    return created


def seed_sample_facilities(db: Session):
    """Seed some sample facilities for testing"""
    cascadia = db.query(models.Brand).filter(models.Brand.slug == "cascadia").first()
    olympus = db.query(models.Brand).filter(models.Brand.slug == "olympus").first()

    if not cascadia or not olympus:
        return []

    facilities = [
        # Cascadia facilities
        {"brand_id": cascadia.id, "name": "Cascadia Care Center", "city": "Portland", "state": "OR"},
        {"brand_id": cascadia.id, "name": "Mountain View SNF", "city": "Seattle", "state": "WA"},
        {"brand_id": cascadia.id, "name": "Evergreen Health & Rehab", "city": "Boise", "state": "ID"},
        # Olympus facilities
        {"brand_id": olympus.id, "name": "Olympus Heights", "city": "San Diego", "state": "CA"},
        {"brand_id": olympus.id, "name": "Sunset Retirement Village", "city": "Phoenix", "state": "AZ"},
    ]

    created = []
    for facility_data in facilities:
        existing = db.query(models.WNFacility).filter(
            models.WNFacility.brand_id == facility_data["brand_id"],
            models.WNFacility.name == facility_data["name"]
        ).first()
        if not existing:
            facility = models.WNFacility(**facility_data)
            db.add(facility)
            created.append(facility_data["name"])
    db.commit()
    return created


def run_seed():
    """Run all seed functions"""
    db = SessionLocal()
    try:
        print("Seeding Welcome Nights data...")

        brands = seed_brands(db)
        print(f"  Created brands: {brands if brands else 'None (already exist)'}")

        games = seed_games(db)
        print(f"  Created games: {games if games else 'None (already exist)'}")

        templates = seed_agenda_templates(db)
        print(f"  Created templates: {templates if templates else 'None (already exist)'}")

        content = seed_reusable_content(db)
        print(f"  Created content: {content if content else 'None (already exist)'}")

        facilities = seed_sample_facilities(db)
        print(f"  Created facilities: {facilities if facilities else 'None (already exist)'}")

        print("Seed completed!")

    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
