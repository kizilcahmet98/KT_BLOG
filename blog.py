from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, SelectField, TextAreaField, PasswordField, validators, StringField
from passlib.hash import sha256_crypt
from functools import wraps


# Kayıt Formu
class RegisterForm(Form):
    name = StringField("Ad Soyad", validators=[validators.Length(min = 4, max = 25)])
    username = StringField("Kullanıcı Adı", validators=[validators.Length(min = 5, max = 35)])
    email = StringField("E mail", validators=[validators.Email(message = "Geçersiz email")])
    password = PasswordField("Şifre", validators = 
        [
        validators.DataRequired(message= "Lütfen parola girin."),
        validators.EqualTo(fieldname= "confirm", message="Parola uyuşmuyor"),
        validators.Length(min = 4, max = 25)
        ])
    confirm = PasswordField("Şifre Tekrar")


# Giriş Formu
class LoginForm(Form):
    username = StringField("Kullancı Girişi:")
    password = PasswordField("Parola:")


# Makale Formu
class ArticleForm(Form):
    title = StringField("Başlık", validators=[validators.Length(min = 5, max = 100)])
    content = TextAreaField("İçerik", validators=[validators.Length(min = 10)])


# decoratör fonksiyon giriş yapılmış mı ?
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Lütfen Önce Giriş Yapın.","danger")
            return redirect(url_for("login"))
    return decorated_function

app = Flask(__name__)

app.secret_key = "ybblog"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "ybblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

#kayıt olma
@app.route("/register",methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()
        sorgu = "INSERT INTO users(name,email,username,password) VALUES(%s,%s,%s,%s)"

        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit()
        cursor.close()
        flash("Başarıyla kayıt oldunuz.", "success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html",form = form)

# Giriş İşlemi
@app.route("/login",methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)

    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data
        
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM users WHERE username = %s"
        result = cursor.execute(sorgu,(username,))

        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]

            if sha256_crypt.verify(password_entered, real_password):
                flash("Başarılı Giriş","success")
                session["logged_in"] = True
                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Parolanızı Yalnış Girdiniz","danger")
                return redirect(url_for("login"))
        else:
            flash("Kullanıcı Adı Geçersiz.", "danger") 
            return redirect(url_for("login"))
    else:
        return render_template("login.html", form = form)

# Çıkış
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# Kontrol Paneli
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s"
    result = cursor.execute(sorgu,(session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles = articles)
    else:
        return render_template("dashboard.html")

# Makale Ekleme
@app.route("/addarticle",methods = ["GET","POST"])
def addarticle():
    form = ArticleForm(request.form)
    
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        sorgu = "INSERT INTO articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))

        mysql.connection.commit()
        cursor.close()

        flash("Makale Başarıla Eklendi","success")
        return redirect(url_for("dashboard"))
    else:
        return render_template("addarticle.html", form = form)

# Makale Silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s and id = %s"
    result = cursor.execute(sorgu,(session["username"],id))

    if result > 0:
        sorgu2 = "DELETE FROM articles WHERE id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        sorgu3 = "SELECT * FROM articles WHERE id = %s"
        result = cursor.execute(sorgu3,(id,))
        
        # makale yok mu yoksa başkasına mı ait sorgula
        if result > 0:
            flash("BU MAKALEYİ SİLMEYE YETKİNİZ YOK.","danger")   
            return redirect(url_for("index"))
        else:
            flash("MAKALE BULUNAMADI.","danger")
            return redirect(url_for("index"))

# Makale Güncelle
@app.route("/edit/<string:id>", methods = ["GET", "POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE author = %s and id = %s"
        result = cursor.execute(sorgu,(session["username"],id))
        
        if result == 0:
            flash("Makale veya yetki yok","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html", form = form)
    else:
        # Post Request
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data

        sorgu2 = "UPDATE articles SET title = %s, content = %s, id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,id))
        mysql.connection.commit()

        flash("Makale başarıyla güncellendi", "success")
        return redirect(url_for("dashboard"))

# Makaleler
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles"
    result  = cursor.execute(sorgu)
    
    if result > 0 :
        articles = cursor.fetchall()
        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")

# Makaleler Kişisel
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE id = %s"
    result = cursor.execute(sorgu,(id,)) 

    if result > 0: 
        article = cursor.fetchone()
        return render_template("article.html", article = article)
    else:
       return render_template("article.html")

# Arama URL
@app.route("/search", methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword") 
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE title LIKE '%" + keyword + "%'"
        result = cursor.execute(sorgu)

        if result == 0:
            flash("Bulunamadı", "warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html", articles = articles)

if __name__ == "__main__":
    app.run(debug=True)
