from flask_login import current_user

ADMIN_ROLE_ID = 1
MODERATOR_ROLE_ID = 2
USER_ROLE_ID = 3
TEACHER_ROLE_ID = 4

def is_admin():
    return current_user.role_id == ADMIN_ROLE_ID

def is_moderator():
    return current_user.role_id == MODERATOR_ROLE_ID

def is_user():
    return current_user.role_id == USER_ROLE_ID

def is_teacher():
    return current_user.role_id == TEACHER_ROLE_ID

class UsersPolicy:
    def __init__(self, record=None):
        self.record = record

    def edit(self):
        return is_admin() or is_moderator()  or is_teacher()

    def show(self):
        return is_admin() or is_moderator() or is_user() or is_teacher()

    def new(self):
        return is_admin() or is_teacher()

    def delete(self):
        return is_admin()

    # def users_review(self):
    #     return is_user()

    def users_review(self):
        return is_user() or is_admin() or is_moderator()

    def moder_review(self):
        return is_moderator() or is_admin() 
        