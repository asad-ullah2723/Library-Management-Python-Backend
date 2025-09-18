from database import SessionLocal
import models

def run():
    db = SessionLocal()
    try:
        email = "mirzasad78@gmail.com"
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            print("User not found:", email)
            return
        try:
            print("Before:", user.id, user.email, user.role, user.is_active)
        except Exception as e:
            print("Could not access attributes directly:", e)
            print("Type:", type(user))
            try:
                print("repr:", repr(user))
            except Exception:
                pass
            # Show available attributes
            try:
                print("dir:", dir(user))
            except Exception:
                pass
            try:
                print("__dict__:", getattr(user, "__dict__", None))
            except Exception:
                pass
        # Attempt to set role and active flag more defensively
        # The current models.py uses `is_superuser` instead of a `role` enum.
        try:
            setattr(user, 'is_superuser', True)
            setattr(user, 'is_active', True)
        except Exception as e:
            print("Error setting attributes:", e)
        db.commit()
        db.refresh(user)
        # Print available attributes defensively
        try:
            print("After:", user.id, user.email, getattr(user, 'is_superuser', None), user.is_active)
        except Exception:
            print("After update - could not read all attributes")
        print("User promoted to admin:", email)
    except Exception as e:
        print("Error:", e)
    finally:
        db.close()

if __name__ == "__main__":
    run()
