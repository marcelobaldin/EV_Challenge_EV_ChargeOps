#!/usr/bin/env python3
"""
EV ChargeOps - Aplicacao Web Flask
Plataforma de Gestao Compartilhada de Recarga para Condominios

Challenge FIAP + GoodWe 2026
Marcelo Bastianello Baldin - RM568746
"""

import csv
import io
from functools import wraps
from datetime import datetime

from flask import (Flask, render_template, request, redirect,
                   url_for, session, jsonify, Response)

from ev_chargeops import (EVChargeOps, MotorIA, GoodWeAPISimulator,
                          SessaoRecarga)

# ============================================================================
# INICIALIZACAO
# ============================================================================

app = Flask(__name__)
app.secret_key = 'ev_chargeops_fiap_goodwe_2026'

print("=" * 60)
print("  EV ChargeOps - Inicializando plataforma...")
print("=" * 60)

plataforma = EVChargeOps()
plataforma.setup_demo()
plataforma.gerar_historico_simulado(dias=30)

print("  Plataforma pronta.\n")

# ============================================================================
# USUARIOS E AUTENTICACAO
# ============================================================================

USERS = {
    'morador': {
        'senha': 'senha',
        'perfil': 'morador',
        'nome': 'Ana Silva',
        'unidade_idx': 0
    },
    'sindico': {
        'senha': 'senha',
        'perfil': 'sindico',
        'nome': 'Administrador do Condominio',
        'unidade_idx': None
    },
    'administrador': {
        'senha': 'senha',
        'perfil': 'administrador',
        'nome': 'Gestao Administrativa',
        'unidade_idx': None
    }
}


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logado'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def perfil_required(*perfis):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('perfil') not in perfis:
                return jsonify({'erro': 'Acesso nao autorizado'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


# ============================================================================
# HELPERS
# ============================================================================

def serializar_sessao(sessao):
    return {
        'id': sessao.id,
        'unidade_id': sessao.unidade_id,
        'carregador_id': sessao.carregador_id,
        'inicio': sessao.inicio.strftime('%d/%m/%Y %H:%M') if sessao.inicio else None,
        'inicio_iso': sessao.inicio.isoformat() if sessao.inicio else None,
        'fim': sessao.fim.strftime('%d/%m/%Y %H:%M') if sessao.fim else None,
        'duracao_h': round((sessao.fim - sessao.inicio).total_seconds() / 3600, 1) if sessao.fim and sessao.inicio else 0,
        'energia_kwh': round(sessao.energia_kwh, 1),
        'custo_total': round(sessao.custo_total, 2),
        'tarifa_aplicada': round(sessao.tarifa_aplicada, 2),
        'status': sessao.status,
        'tipo_tarifa': sessao.tipo_tarifa,
        'potencia_media_kw': round(sessao.potencia_media_kw, 1)
    }


def get_unidade_morador():
    idx = USERS[session['usuario']]['unidade_idx']
    return plataforma.unidades[idx]


def get_sessoes_unidade(unidade):
    return [s for s in plataforma.gerenciador.sessoes
            if s.unidade_id == unidade.id and s.status == 'finalizada']


def nome_unidade(unidade_id):
    for u in plataforma.unidades:
        if u.id == unidade_id:
            return f"{u.numero}-{u.bloco}"
    return unidade_id


def proprietario_unidade(unidade_id):
    for u in plataforma.unidades:
        if u.id == unidade_id:
            return u.proprietario
    return ""


# ============================================================================
# ROTAS DE PAGINA
# ============================================================================

@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip().lower()
        senha = request.form.get('senha', '').strip()

        if usuario in USERS and USERS[usuario]['senha'] == senha:
            session['logado'] = True
            session['usuario'] = usuario
            session['perfil'] = USERS[usuario]['perfil']
            session['nome'] = USERS[usuario]['nome']
            return redirect(url_for('dashboard'))
        else:
            erro = 'Usuario ou senha incorretos'

    return render_template('login.html', erro=erro)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    perfil = session.get('perfil')
    nome = session.get('nome')
    cond_nome = plataforma.condominio.nome
    return render_template('dashboard.html',
                           perfil=perfil, nome=nome,
                           condominio=cond_nome)


# ============================================================================
# API — PERFIL DO USUARIO
# ============================================================================

@app.route('/api/perfil')
@login_required
def api_perfil():
    usuario = session['usuario']
    user = USERS[usuario]
    dados = {
        'usuario': usuario,
        'perfil': user['perfil'],
        'nome': user['nome']
    }
    if user['unidade_idx'] is not None:
        u = plataforma.unidades[user['unidade_idx']]
        dados['unidade'] = f"{u.numero}-{u.bloco}"
        dados['proprietario'] = u.proprietario
    return jsonify(dados)


# ============================================================================
# API — MORADOR
# ============================================================================

@app.route('/api/morador/dashboard')
@login_required
@perfil_required('morador')
def api_morador_dashboard():
    unidade = get_unidade_morador()
    sessoes = get_sessoes_unidade(unidade)

    total_kwh = sum(s.energia_kwh for s in sessoes)
    total_custo = sum(s.custo_total for s in sessoes)
    n_sessoes = len(sessoes)
    media = total_kwh / n_sessoes if n_sessoes > 0 else 0

    dist_tarifa = {}
    for s in sessoes:
        dist_tarifa[s.tipo_tarifa] = dist_tarifa.get(s.tipo_tarifa, 0) + 1

    consumo_diario = {}
    for s in sessoes:
        dia = s.inicio.strftime('%Y-%m-%d') if s.inicio else None
        if dia:
            consumo_diario[dia] = consumo_diario.get(dia, 0) + s.energia_kwh

    dias_ord = sorted(consumo_diario.keys())

    return jsonify({
        'unidade': f"{unidade.numero}-{unidade.bloco}",
        'proprietario': unidade.proprietario,
        'total_kwh': round(total_kwh, 1),
        'total_custo': round(total_custo, 2),
        'total_sessoes': n_sessoes,
        'media_kwh': round(media, 1),
        'distribuicao_tarifa': dist_tarifa,
        'consumo_diario': {
            'labels': [d[5:].replace('-', '/') for d in dias_ord],
            'valores': [round(consumo_diario[d], 1) for d in dias_ord]
        }
    })


@app.route('/api/morador/sessoes')
@login_required
@perfil_required('morador')
def api_morador_sessoes():
    unidade = get_unidade_morador()
    sessoes = get_sessoes_unidade(unidade)
    sessoes.sort(key=lambda s: s.inicio or datetime.min, reverse=True)
    return jsonify([serializar_sessao(s) for s in sessoes])


@app.route('/api/morador/recomendacoes')
@login_required
@perfil_required('morador')
def api_morador_recomendacoes():
    unidade = get_unidade_morador()
    sessoes = get_sessoes_unidade(unidade)

    custo_real = sum(s.custo_total for s in sessoes)
    custo_fora_ponta = sum(s.energia_kwh * plataforma.condominio.tarifa_kwh_base
                          for s in sessoes)
    economia_possivel = custo_real - custo_fora_ponta

    n_ponta = sum(1 for s in sessoes if s.tipo_tarifa == 'ponta')
    n_inter = sum(1 for s in sessoes if s.tipo_tarifa == 'intermediaria')
    n_fora = sum(1 for s in sessoes if s.tipo_tarifa == 'fora_ponta')
    total = len(sessoes) or 1

    interpretacoes = []
    for s in sessoes[-5:]:
        interpretacoes.append(plataforma.motor_ia.interpretar_sessao(s))

    return jsonify({
        'economia_possivel': round(max(economia_possivel, 0), 2),
        'melhores_horarios': [
            {'faixa': '22h - 05h', 'tarifa': 'R$ 0,85/kWh', 'desconto': 'Tarifa base'},
            {'faixa': '05h - 17h', 'tarifa': 'R$ 0,85/kWh', 'desconto': 'Fora ponta'},
            {'faixa': '17h - 18h', 'tarifa': 'R$ 1,02/kWh', 'desconto': 'Intermediaria (+20%)'},
            {'faixa': '18h - 21h', 'tarifa': 'R$ 1,28/kWh', 'desconto': 'Ponta (+50%)'},
            {'faixa': '21h - 22h', 'tarifa': 'R$ 1,02/kWh', 'desconto': 'Intermediaria (+20%)'},
        ],
        'perfil_uso': {
            'ponta_pct': round(n_ponta / total * 100, 1),
            'intermediaria_pct': round(n_inter / total * 100, 1),
            'fora_ponta_pct': round(n_fora / total * 100, 1)
        },
        'dica': ('Voce tem {} sessoes em horario de ponta. '
                 'Carregar apos as 22h pode economizar ate R$ {:.2f}/mes.').format(
                     n_ponta, economia_possivel / max(1, len(set(s.inicio.month for s in sessoes if s.inicio)))),
        'interpretacoes': interpretacoes
    })


@app.route('/api/morador/eletropostos')
@login_required
@perfil_required('morador')
def api_morador_eletropostos():
    dados = plataforma.buscar_eletropostos_proximos()
    return jsonify(dados)


# ============================================================================
# API — SINDICO
# ============================================================================

@app.route('/api/sindico/dashboard')
@login_required
@perfil_required('sindico')
def api_sindico_dashboard():
    dash = plataforma.dashboard_condominio()

    consumo_unidade = []
    for uid, kwh in dash['consumo_por_unidade'].items():
        consumo_unidade.append({
            'unidade': nome_unidade(uid),
            'proprietario': proprietario_unidade(uid),
            'kwh': round(kwh, 1)
        })
    consumo_unidade.sort(key=lambda x: x['kwh'], reverse=True)

    sessoes_fin = [s for s in plataforma.gerenciador.sessoes if s.status == 'finalizada']

    consumo_diario = {}
    for s in sessoes_fin:
        dia = s.inicio.strftime('%Y-%m-%d') if s.inicio else None
        if dia:
            consumo_diario[dia] = consumo_diario.get(dia, 0) + s.energia_kwh
    dias_ord = sorted(consumo_diario.keys())

    dist_horario = {}
    for s in sessoes_fin:
        if s.inicio:
            h = s.inicio.hour
            dist_horario[h] = dist_horario.get(h, 0) + 1

    return jsonify({
        'condominio': dash['condominio'],
        'total_sessoes': dash['total_sessoes'],
        'total_kwh': dash['total_kwh'],
        'total_custo': dash['total_custo'],
        'media_kwh_sessao': dash['media_kwh_sessao'],
        'unidades_ativas': dash['unidades_ativas'],
        'carregadores_disponiveis': dash['carregadores_disponiveis'],
        'total_carregadores': dash['total_carregadores'],
        'hora_pico': f"{dash['hora_pico']}h",
        'distribuicao_tarifa': dash['distribuicao_tarifa'],
        'consumo_por_unidade': consumo_unidade,
        'consumo_diario': {
            'labels': [d[5:].replace('-', '/') for d in dias_ord],
            'valores': [round(consumo_diario[d], 1) for d in dias_ord]
        },
        'distribuicao_horario': {
            'labels': [f"{h}h" for h in range(24)],
            'valores': [dist_horario.get(h, 0) for h in range(24)]
        }
    })


@app.route('/api/sindico/ranking')
@login_required
@perfil_required('sindico')
def api_sindico_ranking():
    sessoes_fin = [s for s in plataforma.gerenciador.sessoes if s.status == 'finalizada']

    ranking = {}
    for u in plataforma.unidades:
        s_u = [s for s in sessoes_fin if s.unidade_id == u.id]
        ranking[u.id] = {
            'unidade': f"{u.numero}-{u.bloco}",
            'proprietario': u.proprietario,
            'sessoes': len(s_u),
            'kwh': round(sum(s.energia_kwh for s in s_u), 1),
            'custo': round(sum(s.custo_total for s in s_u), 2)
        }

    lista = sorted(ranking.values(), key=lambda x: x['kwh'], reverse=True)
    return jsonify(lista)


@app.route('/api/sindico/carregadores')
@login_required
@perfil_required('sindico')
def api_sindico_carregadores():
    return jsonify(plataforma.status_carregadores())


@app.route('/api/sindico/analise-ia')
@login_required
@perfil_required('sindico')
def api_sindico_analise_ia():
    analise = plataforma.executar_analise_ia()
    return jsonify(analise)


@app.route('/api/sindico/chat', methods=['POST'])
@login_required
@perfil_required('sindico')
def api_sindico_chat():
    dados = request.get_json()
    pergunta = dados.get('pergunta', '')
    if not pergunta.strip():
        return jsonify({'resposta': 'Por favor, digite uma pergunta.'})

    analise = plataforma.executar_analise_ia()
    dados_sindico = analise['dados_sindico']
    resposta = plataforma.motor_ia.sindico_virtual(pergunta, dados_sindico)
    return jsonify({'resposta': resposta})


@app.route('/api/sindico/anomalias')
@login_required
@perfil_required('sindico')
def api_sindico_anomalias():
    sessoes_fin = [s for s in plataforma.gerenciador.sessoes if s.status == 'finalizada']
    anomalias = plataforma.motor_ia.detectar_anomalias(sessoes_fin)
    return jsonify(anomalias)


@app.route('/api/sindico/previsao')
@login_required
@perfil_required('sindico')
def api_sindico_previsao():
    sessoes_fin = [s for s in plataforma.gerenciador.sessoes if s.status == 'finalizada']
    previsao = plataforma.motor_ia.prever_demanda(sessoes_fin)
    return jsonify(previsao)


# ============================================================================
# API — ADMINISTRADOR
# ============================================================================

@app.route('/api/admin/faturas')
@login_required
@perfil_required('administrador')
def api_admin_faturas():
    faturas = []
    for f in plataforma.faturamento.faturas:
        for u in plataforma.unidades:
            if u.id == f.unidade_id:
                faturas.append({
                    'id': f.id,
                    'unidade': f"{u.numero}-{u.bloco}",
                    'proprietario': u.proprietario,
                    'mes_referencia': f.mes_referencia,
                    'total_sessoes': len(f.sessoes),
                    'total_kwh': round(f.total_kwh, 1),
                    'total_reais': round(f.total_reais, 2),
                    'status': f.status,
                    'data_emissao': f.data_emissao.strftime('%d/%m/%Y') if f.data_emissao else None,
                    'data_vencimento': f.data_vencimento.strftime('%d/%m/%Y') if f.data_vencimento else None
                })
                break
    return jsonify(faturas)


@app.route('/api/admin/fatura-gerar', methods=['POST'])
@login_required
@perfil_required('administrador')
def api_admin_fatura_gerar():
    agora = datetime.now()
    mes_ref = agora.strftime('%Y-%m')

    ja_existe = any(f.mes_referencia == mes_ref for f in plataforma.faturamento.faturas)
    if ja_existe:
        return jsonify({'status': 'ja_gerada', 'mensagem': f'Faturas de {mes_ref} ja foram geradas.'})

    sessoes_fin = [s for s in plataforma.gerenciador.sessoes if s.status == 'finalizada']
    faturas_geradas = []

    for u in plataforma.unidades:
        sessoes_u = [s for s in sessoes_fin if s.unidade_id == u.id]
        if sessoes_u:
            fatura = plataforma.faturamento.gerar_fatura_mensal(u, sessoes_u, mes_ref)
            faturas_geradas.append({
                'unidade': f"{u.numero}-{u.bloco}",
                'proprietario': u.proprietario,
                'sessoes': len(sessoes_u),
                'kwh': round(fatura.total_kwh, 1),
                'reais': round(fatura.total_reais, 2)
            })

    return jsonify({
        'status': 'ok',
        'mensagem': f'{len(faturas_geradas)} faturas geradas para {mes_ref}',
        'faturas': faturas_geradas
    })


@app.route('/api/admin/rateio')
@login_required
@perfil_required('administrador')
def api_admin_rateio():
    sessoes_fin = [s for s in plataforma.gerenciador.sessoes if s.status == 'finalizada']
    mes_ref = datetime.now().strftime('%Y-%m')
    rateio = plataforma.faturamento.relatorio_rateio(plataforma.unidades, sessoes_fin, mes_ref)
    rpu = rateio.get('rateio_por_unidade', {})
    total_kwh = sum(v.get('kwh', 0) for v in rpu.values()) if isinstance(rpu, dict) else 0
    total_custo = rateio.get('total_condominio_reais', 0)
    lista = []
    if isinstance(rpu, dict):
        for numero, dados in rpu.items():
            lista.append({
                'unidade': f"{numero}-{dados.get('bloco', '')}",
                'proprietario': dados.get('proprietario', ''),
                'sessoes': dados.get('sessoes', 0),
                'kwh': round(dados.get('kwh', 0), 1),
                'custo': round(dados.get('custo', 0), 2)
            })
        lista.sort(key=lambda x: x['kwh'], reverse=True)
    return jsonify({
        'mes_referencia': mes_ref,
        'total_kwh': round(total_kwh, 1),
        'total_custo': round(total_custo, 2),
        'rateio_por_unidade': lista
    })


@app.route('/api/admin/export-csv')
@login_required
@perfil_required('administrador')
def api_admin_export_csv():
    sessoes_fin = [s for s in plataforma.gerenciador.sessoes if s.status == 'finalizada']
    mes_ref = datetime.now().strftime('%Y-%m')

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Unidade', 'Bloco', 'Proprietario', 'Sessoes',
                     'kWh Total', 'Custo Total (R$)'])

    for u in plataforma.unidades:
        s_u = [s for s in sessoes_fin if s.unidade_id == u.id]
        kwh = sum(s.energia_kwh for s in s_u)
        custo = sum(s.custo_total for s in s_u)
        writer.writerow([u.numero, u.bloco, u.proprietario, len(s_u),
                         f"{kwh:.1f}", f"{custo:.2f}"])

    total_kwh = sum(s.energia_kwh for s in sessoes_fin)
    total_custo = sum(s.custo_total for s in sessoes_fin)
    writer.writerow(['TOTAL', '', '', len(sessoes_fin),
                     f"{total_kwh:.1f}", f"{total_custo:.2f}"])

    csv_content = output.getvalue()
    output.close()

    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=rateio_{mes_ref}.csv'}
    )


@app.route('/api/admin/historico')
@login_required
@perfil_required('administrador')
def api_admin_historico():
    meses = {}
    for f in plataforma.faturamento.faturas:
        m = f.mes_referencia
        if m not in meses:
            meses[m] = {'mes': m, 'unidades': 0, 'kwh': 0, 'reais': 0, 'pagas': 0, 'abertas': 0}
        meses[m]['unidades'] += 1
        meses[m]['kwh'] += f.total_kwh
        meses[m]['reais'] += f.total_reais
        if f.status == 'paga':
            meses[m]['pagas'] += 1
        else:
            meses[m]['abertas'] += 1

    for m in meses:
        meses[m]['kwh'] = round(meses[m]['kwh'], 1)
        meses[m]['reais'] = round(meses[m]['reais'], 2)

    return jsonify(sorted(meses.values(), key=lambda x: x['mes'], reverse=True))


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("  EV ChargeOps - Sistema Web")
    print("  Acesse: http://localhost:5050")
    print("  Perfis: morador/senha | sindico/senha | administrador/senha")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5050, debug=False)
