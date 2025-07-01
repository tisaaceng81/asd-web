from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from analisador import analisar_sistema
import os

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)

    # Garante que a pasta instance/ existe
    os.makedirs(app.instance_path, exist_ok=True)

    # Caminho absoluto do banco na pasta instance
    db_path = os.path.join(app.instance_path, 'usuarios.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    class Usuario(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(150), unique=True, nullable=False)
        senha_hash = db.Column(db.String(150), nullable=False)
        aprovado = db.Column(db.Boolean, default=False)

    with app.app_context():
        db.create_all()

        # Cria e aprova admin automaticamente
        admin_email = 'tisaaceng@gmail.com'
        admin_senha = '4839AT81'
        admin = Usuario.query.filter_by(email=admin_email).first()

        if not admin:
            admin = Usuario(
                email=admin_email,
                senha_hash=generate_password_hash(admin_senha),
                aprovado=True
            )
            db.session.add(admin)
        else:
            admin.aprovado = True
            admin.senha_hash = generate_password_hash(admin_senha)

        db.session.commit()

    @app.route('/', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form['email']
            senha = request.form['senha']
            usuario = Usuario.query.filter_by(email=email).first()
            if usuario and check_password_hash(usuario.senha_hash, senha):
                if usuario.aprovado:
                    session['user_id'] = usuario.id
                    return redirect(url_for('dashboard'))
                else:
                    flash('Seu cadastro ainda não foi aprovado pelo administrador.', 'warning')
            else:
                flash('Email ou senha incorretos.', 'danger')
        return render_template('login.html')

    @app.route('/cadastro', methods=['GET', 'POST'])
    def cadastro():
        if request.method == 'POST':
            email = request.form['email']
            senha = request.form['senha']
            if Usuario.query.filter_by(email=email).first():
                flash('Email já cadastrado.', 'warning')
                return redirect(url_for('cadastro'))
            senha_hash = generate_password_hash(senha)
            novo_usuario = Usuario(email=email, senha_hash=senha_hash, aprovado=False)
            db.session.add(novo_usuario)
            db.session.commit()
            flash('Cadastro realizado com sucesso! Aguarde aprovação do administrador.', 'success')
            return redirect(url_for('login'))
        return render_template('cadastro.html')

    @app.route('/dashboard', methods=['GET', 'POST'])
    def dashboard():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        if request.method == 'POST':
            eq_diff = request.form['equacao']
            var_entrada = request.form['entrada']
            var_saida = request.form['saida']
            metodo_sintonia = request.form['metodo_sintonia']

            try:
                resultados = analisar_sistema(eq_diff, var_entrada, var_saida, metodo_sintonia)
                return render_template('dashboard.html', resultados=resultados, eq_diff=eq_diff,
                                       var_entrada=var_entrada, var_saida=var_saida,
                                       metodo_sintonia=metodo_sintonia)
            except Exception as e:
                flash(f'Erro na análise: {e}', 'danger')
                return render_template('dashboard.html')

        return render_template('dashboard.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('Desconectado com sucesso.', 'info')
        return redirect(url_for('login'))

    @app.route('/admin', methods=['GET', 'POST'])
    def admin():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        usuario = Usuario.query.get(session['user_id'])
        if not usuario or usuario.email != 'tisaaceng@gmail.com':
            flash('Acesso negado.', 'danger')
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            aprovar_id = request.form.get('aprovar')
            if aprovar_id:
                usuario_aprovar = Usuario.query.get(int(aprovar_id))
                if usuario_aprovar:
                    usuario_aprovar.aprovado = True
                    db.session.commit()
                    flash(f'Usuário {usuario_aprovar.email} aprovado!', 'success')

        usuarios_pendentes = Usuario.query.filter_by(aprovado=False).all()
        return render_template('admin.html', usuarios=usuarios_pendentes)

    return app

# Para rodar localmente com `python app.py`
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)