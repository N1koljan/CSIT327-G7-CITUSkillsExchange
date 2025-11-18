import hashlib

def get_conversation_id(user1, user2):
    uid1, uid2 = sorted([user1.id, user2.id])
    return f"chat_{uid1}_{uid2}"
