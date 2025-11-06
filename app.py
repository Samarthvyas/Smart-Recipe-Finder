from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import requests

# -------------------- APP SETUP --------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recipes.db'
app.config['SECRET_KEY'] = 'your_secret_key'

# -------------------- EXTENSIONS --------------------
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

API_KEY="5c897cded07140028a9974875df9ed85"


# -------------------- DATABASE MODELS --------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    instructions = db.Column(db.Text)
    image = db.Column(db.String(300))


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipe_title = db.Column(db.String(150))
    image_url = db.Column(db.String(300))


# -------------------- LOGIN MANAGER --------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# -------------------- ROUTES --------------------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            flash("User already exists! Try logging in.", "danger")
            return redirect(url_for("login"))

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        new_user = User(username=username, email=email, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("search"))
        else:
            flash("Invalid email or password!", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if request.method == 'POST':
        ingredients = request.form.get('ingredients')
        url = f"https://api.spoonacular.com/recipes/findByIngredients?ingredients={ingredients}&number=5&apiKey={API_KEY}"
        response = requests.get(url)
        recipes = response.json() if response.status_code == 200 else []
        return render_template('results.html', recipes=recipes)
    return render_template('search.html')

@app.route('/save_recipe', methods=['POST'])
@login_required
def save_recipe():
    title = request.form.get('title')
    image = request.form.get('image')

    # Check if already saved
    existing = Favorite.query.filter_by(user_id=current_user.id, recipe_title=title).first()
    if existing:
        flash('Recipe already in favorites!', 'warning')
    else:
        fav = Favorite(recipe_title=title, image_url=image, user_id=current_user.id)
        db.session.add(fav)
        db.session.commit()
        flash('Recipe saved to favorites!', 'success')

    return redirect(url_for('view_favorites'))

@app.route('/favorites')
@login_required
def view_favorites():
    favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    return render_template('favorites.html', favorites=favorites)

@app.route('/remove_favorite/<int:id>')
@login_required
def remove_favorite(id):
    fav = Favorite.query.get_or_404(id)
    if fav.user_id == current_user.id:
        db.session.delete(fav)
        db.session.commit()
        flash('Removed from favorites.', 'info')
    return redirect(url_for('view_favorites'))



# -------------------- RUN APP --------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
