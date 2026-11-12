CATEGORIES = [
    "Overflowing Bin",
    "Illegal Dumping",
    "Delayed Collection",
    "Hazardous Waste",
    "Construction Debris",
    "Dead Animal",
    "Blocked Drain / Waste in Drain",
    "Other",
]
STATUSES = ["Pending", "Assigned", "In Progress", "Collected", "Rejected"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
PRIORITY_COLORS = {            # RGB for map markers
    "Low": [34, 197, 94],
    "Medium": [250, 204, 21],
    "High": [249, 115, 22],
    "Critical": [220, 38, 38],
}
DEFAULT_LAT, DEFAULT_LON = 23.8103, 90.4125   # Dhaka
DEFAULT_ADMIN_EMAIL = "admin@city.gov"
DEFAULT_ADMIN_PASSWORD = "admin123"
