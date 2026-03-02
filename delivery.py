def get_delivery_time(address):
    address_lower = address.lower()

    island_areas = [
        "lekki", "vi", "victoria island", "ikoyi",
        "ajah", "sangotedo", "chevron", "ikate",
        "admiralty", "eti-osa", "lagos island"
    ]

    mainland_areas = [
        "ikeja", "surulere", "yaba", "maryland",
        "ogba", "agege", "isolo", "mushin",
        "oshodi", "festac", "amuwo"
    ]

    far_areas = [
        "ikorodu", "badagry", "epe", "agbara",
        "mowe", "ibafo", "sagamu"
    ]

    if any(area in address_lower for area in island_areas):
        minutes = 25
        zone = "Lagos Island"
    elif any(area in address_lower for area in far_areas):
        minutes = 75
        zone = "Far Area"
    elif any(area in address_lower for area in mainland_areas):
        minutes = 50
        zone = "Lagos Mainland"
    else:
        minutes = 40
        zone = "Lagos"

    return {
        "success": True,
        "total_minutes": minutes,
        "message": f"Estimated delivery time: *{minutes} minutes* \n({zone} delivery)"
    }