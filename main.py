import db_utils
import login_window


if __name__ == "__main__":
    db_utils.create_tables()
    login_window.show_login_window()

