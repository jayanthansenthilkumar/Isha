"""
Database models for Isha Framework Landing Page
"""

# This landing page is static — no database models needed.
# But here's an example of what Isha ORM looks like:
#
# from isha.orm import Database, Model, TextField, IntegerField, BooleanField
#
# db = Database("isha_landing.db")
#
# class Subscriber(Model):
#     _table = "subscribers"
#     _db = db
#     email = TextField()
#     name  = TextField()
