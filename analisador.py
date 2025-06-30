import numpy as np
import matplotlib.pyplot as plt
import sympy as sp
from sympy import symbols, simplify
from control.matlab import tf, step
from io import BytesIO
import base64

def sobrescrito(numero):
    """Converte um número inteiro para sobrescrito unicode para exibição."""
    subscritos = str.maketrans("0123456789-+", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺")
    return str(numero).translate(subscritos)

def formatar_funcao_transferencia(num, den):
    """
    Retorna string formatada com barra horizontal, expoentes sobrescritos e "." no lugar de "*".
    """
    def polinomio_str(coefs):
        grau = len(coefs) - 1
        termos = []
        for i, coef in enumerate(coefs):
            if abs(coef) < 1e-12:
                continue
            pot = grau - i
            coef_str = f"{abs(coef):g}"
            if pot > 1:
                pot_str = f"s{superscrito(pot)}"
            elif pot == 1:
                pot_str = "s"
            else:
                pot_str = ""
            if coef < 0:
                termo = f"- {coef_str}.{pot_str}"
            else:
                termo = f"+ {coef_str}.{pot_str}"
            termos.append(termo)
        if not termos:
            return "0"
        resultado = " ".join(termos)
        if resultado.startswith("+ "):
            resultado = resultado[2:]
        elif resultado.startswith("- "):
            resultado = "-" + resultado[2:]
        resultado = resultado.replace(". ", " ")
        resultado = resultado.replace(".+", "+").replace(".-", "-")
        resultado = resultado.replace(".s", "s")
        return resultado.strip()

    num_str = polinomio_str(num)
    den_str = polinomio_str(den)
    barra = "―" * max(len(num_str), len(den_str))
    return f"{num_str}\n{barra}\n{den_str}"

def calcular_L_T(malha_aberta_tf):
    """
    Método da curva de reação para estimar L e T da FT de malha aberta.
    """
    t, y = step(malha_aberta_tf, T=np.linspace(0, 50, 5000))
    y_final = y[-1]
    try:
        t_0283 = t[np.where(y >= 0.283 * y_final)[0][0]]
        t_0632 = t[np.where(y >= 0.632 * y_final)[0][0]]
        L = t_0283
        T = (t_0632 - L) / 0.632
        if L < 0: L = 0
        if T < 0: T = 0
    except:
        L = 0
        T = 0
    return L, T

def calcular_PID_ziegler_nichols(L, T):
    """
    Retorna Kp, Ki, Kd com base em Ziegler-Nichols.
    """
    if L == 0 or T == 0:
        return 0, 0, 0
    Kp = 1.2 * (T / L)
    Ti = 2 * L
    Td = 0.5 * L
    Ki = Kp / Ti
    Kd = Kp * Td
    return Kp, Ki, Kd

def criar_funcao_transferencia_pid(Kp, Ki, Kd):
    s = sp.symbols('s')
    return Kp + Ki / s + Kd * s

def funcao_transferencia_malha_aberta(Kp, Ki, Kd, L, T):
    s = sp.symbols('s')
    return sp.exp(-L * s) * (1 / (T * s + 1))

def funcao_transferencia_malha_fechada(G_open, pid):
    return simplify((pid * G_open) / (1 + pid * G_open))

def gerar_diagrama_blocos(Kp, Ki, Kd, L, T):
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    axs[0].axis('off')
    axs[0].set_title("Malha Aberta")
    axs[0].text(0.5, 0.5, f"L = {L:.3f}\nT = {T:.3f}", fontsize=12, ha='center', va='center')
    axs[1].axis('off')
    axs[1].set_title("Malha Fechada")
    axs[1].text(0.5, 0.5, f"Kp = {Kp:.3f}\nKi = {Ki:.3f}\nKd = {Kd:.3f}", fontsize=12, ha='center', va='center')
    buf = BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def analisar_sistema(equacao_diferencial, entrada, saida, metodo_sintonia):
    """
    Função principal usada pelo sistema web.
    """
    s = sp.symbols('s')

    # Exemplo simples substituível por parsing simbólico
    L = 1.0
    T = 2.0
    num = [1]
    den = [T, 1]
    G_open = tf(num, den)

    L, T = calcular_L_T(G_open)
    Kp, Ki, Kd = calcular_PID_ziegler_nichols(L, T)
    pid_tf = criar_funcao_transferencia_pid(Kp, Ki, Kd)
    G_open_sym = funcao_transferencia_malha_aberta(Kp, Ki, Kd, L, T)
    G_closed_sym = funcao_transferencia_malha_fechada(G_open_sym, pid_tf)
    ft_aberta_str = formatar_funcao_transferencia(num, den)
    ft_fechada_latex = sp.latex(G_closed_sym)
    imagem_blocos = gerar_diagrama_blocos(Kp, Ki, Kd, L, T)

    resultados = {
        "L": L,
        "T": T,
        "Kp": Kp,
        "Ki": Ki,
        "Kd": Kd,
        "ft_aberta": ft_aberta_str,
        "ft_fechada_latex": ft_fechada_latex,
        "imagem_blocos": imagem_blocos,
    }
    return resultados 
