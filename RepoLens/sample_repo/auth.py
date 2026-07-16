from permissions import authorize

def authenticate(token):
    return authorize(token)
