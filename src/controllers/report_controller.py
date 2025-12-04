# from fastapi.responses import FileResponse
# from sqlmodel import Session, select
# from datetime import datetime, date, timedelta
# import pandas as pd
# import matplotlib.pyplot as plt
# from matplotlib import rcParams
# from fpdf import FPDF
# from zoneinfo import ZoneInfo
# import os
# from typing import Optional, Dict, Any, List
# import numpy as np
# from PIL import Image
# import io
# import base64

# from src.model.sale import Sales
# from src.model.user import Usuario
# from src.model.employee import Employees
# from src.model.product import Produto
# from src.model.customers import Customer

# # ===============================
# # Configurações de estilo
# # ===============================
# rcParams['font.family'] = 'DejaVu Sans'
# plt.style.use('ggplot')
# # Cores para os gráficos
# COLORS = ['#4C72B0', '#55A868', '#C44E52', '#8172B2', '#CCB974', '#64B5CD']

# # Timezone padrão
# DEFAULT_TZ = ZoneInfo("America/Sao_Paulo")

# # ===============================
# # Função para carregar logo
# # ===============================
# def load_logo(image_path: str = None, base64_string: str = None) -> Optional[str]:
#     """
#     Carrega uma imagem e converte para base64 para inclusão no PDF.
#     Pode receber um caminho de arquivo ou uma string base64.
#     """
#     try:
#         if base64_string:
#             # Verifica se já é uma string base64 válida
#             if isinstance(base64_string, str) and base64_string.startswith('data:image'):
#                 return base64_string
#             else:
#                 # Tenta decodificar para verificar se é base64 válido
#                 base64.b64decode(base64_string)
#                 return f"data:image/png;base64,{base64_string}"

#         elif image_path and os.path.exists(image_path):
#             with open(image_path, "rb") as img_file:
#                 encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
#                 return f"data:image/png;base64,{encoded_string}"

#     except Exception as e:
#         print(f"Erro ao carregar logo: {e}")

#     return None

# # ===============================
# # Funções auxiliares para timezone
# # ===============================
# def ensure_timezone_aware(dt: datetime) -> datetime:
#     """Garante que um datetime seja timezone-aware."""
#     if dt is None:
#         return datetime.now(DEFAULT_TZ)

#     if dt.tzinfo is None:
#         return dt.replace(tzinfo=DEFAULT_TZ)

#     return dt

# def ensure_timezone_aware_series(series: pd.Series) -> pd.Series:
#     """Garante que uma série de datetime seja timezone-aware."""
#     if series.empty:
#         return series

#     if series.dt.tz is None:
#         return series.dt.tz_localize(DEFAULT_TZ)

#     return series

# # ===============================
# # Funções de coleta de dados
# # ===============================

# def fetch_sales_data(session: Session, usuario_id: int, start_date: date = None, end_date: date = None) -> pd.DataFrame:
#     """Busca todas as vendas do usuário e retorna DataFrame."""
#     statement = select(Sales).where(Sales.usuario_id == usuario_id)

#     if start_date:
#         start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=DEFAULT_TZ)
#         statement = statement.where(Sales.criado_em >= start_datetime)

#     if end_date:
#         end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=DEFAULT_TZ)
#         statement = statement.where(Sales.criado_em <= end_datetime)

#     sales = session.exec(statement).all()

#     if not sales:
#         return pd.DataFrame()

#     data = []
#     for s in sales:
#         # Verificação robusta para dados None
#         product_name = s.product_name if s.product_name else "Produto não informado"
#         quantity = s.quantity if s.quantity is not None else 0
#         total_price = s.total_price if s.total_price is not None else 0.0
#         lucro_total = s.lucro_total if s.lucro_total is not None else 0.0
#         cost_price = s.cost_price if s.cost_price is not None else 0.0

#         # Verificação para funcionário
#         if s.funcionario:
#             funcionario_nome = s.funcionario.nome if s.funcionario.nome else "Não informado"
#         else:
#             funcionario_nome = "Não informado"

#         # Verificação para cliente
#         if s.cliente:
#             cliente_id = s.cliente.id
#             cliente_nome = s.cliente.full_name if s.cliente.full_name else f"Cliente {cliente_id}"
#         else:
#             cliente_id = "Desconhecido"
#             cliente_nome = "Cliente não informado"

#         # Verificação para data com timezone
#         criado_em = ensure_timezone_aware(s.criado_em) if s.criado_em else datetime.now(DEFAULT_TZ)

#         # Verificação para código da venda
#         codigo_da_venda = s.codigo_da_venda if s.codigo_da_venda else "N/A"

#         # Verificação para forma de pagamento
#         forma_pagamento = getattr(s, "payment_method", "À vista") if hasattr(s, "payment_method") else "À vista"
#         if not forma_pagamento or forma_pagamento == "":
#             forma_pagamento = "À vista"

#         data.append({
#             "id": s.id,
#             "produto": product_name,
#             "quantidade": quantity,
#             "total_price": total_price,
#             "lucro": lucro_total,
#             "cost_price": cost_price,
#             "funcionario": funcionario_nome,
#             "criado_em": criado_em,
#             "cliente_id": cliente_id,
#             "cliente_nome": cliente_nome,
#             "codigo": codigo_da_venda,
#             "forma_pagamento": forma_pagamento
#         })

#     df = pd.DataFrame(data)

#     if not df.empty and 'criado_em' in df.columns:
#         # Garantir que as datas são timezone-aware
#         df['criado_em'] = ensure_timezone_aware_series(df['criado_em'])

#     return df

# def fetch_products_data(session: Session, usuario_id: int) -> pd.DataFrame:
#     """Busca todos os produtos e retorna DataFrame."""
#     statement = select(Produto).where(Produto.usuario_id == usuario_id)
#     products = session.exec(statement).all()

#     if not products:
#         return pd.DataFrame()

#     data = []
#     for p in products:
#         # Verificação robusta para dados None
#         name = p.name if p.name else "Produto sem nome"
#         stock = p.stock if p.stock is not None else 0
#         stoke_min = p.stoke_min if p.stoke_min is not None else 0
#         stoke_max = p.stoke_max if p.stoke_max is not None else 0

#         # Verificação para data de validade
#         date_expired = p.date_expired if p.date_expired else None

#         data.append({
#             "id": p.id,
#             "nome": name,
#             "stock": stock,
#             "stoke_min": stoke_min,
#             "stoke_max": stoke_max,
#             "date_expired": date_expired,
#         })

#     return pd.DataFrame(data)

# def fetch_customers_data(session: Session, usuario_id: int) -> pd.DataFrame:
#     """Busca todos os clientes e retorna DataFrame."""
#     statement = Customer.filter(id == usuario_id)
#     customers = session.exec(statement).all()

#     if not customers:
#         return pd.DataFrame()

#     data = []
#     for c in customers:
#         # Verificação robusta para dados None
#         full_name = c.full_name if c.full_name else "Cliente sem nome"
#         birth_date = c.birth_date if c.birth_date else None
#         cpf = c.cpf if c.cpf else "Não informado"
#         road = c.road if c.road else "Não informado"
#         house_number = c.house_number if c.house_number else "S/N"
#         neighborhood = c.neighborhood if c.neighborhood else "Não informado"
#         city = c.city if c.city else "Não informado"
#         tel = c.tel if c.tel else "Não informado"
#         cep = c.cep if c.cep else "Não informado"
#         credit = c.credit if c.credit is not None else 0.0
#         current_balance = c.current_balance if c.current_balance is not None else 0.0
#         total_spent = c.total_spent if c.total_spent is not None else 0.0
#         due_date = c.due_date if c.due_date else None
#         status = c.status if c.status else "Ativo"

#         data.append({
#             "id": c.id,
#             "full_name": full_name,
#             "birth_date": birth_date,
#             "cpf": cpf,
#             "road": road,
#             "house_number": house_number,
#             "neighborhood": neighborhood,
#             "city": city,
#             "tel": tel,
#             "cep": cep,
#             "credit": credit,
#             "current_balance": current_balance,
#             "total_spent": total_spent,
#             "due_date": due_date,
#             "status": status,
#         })

#     return pd.DataFrame(data)

# def fetch_employees_data(session: Session, usuario_id: int) -> pd.DataFrame:
#     """Busca todos os funcionários e retorna DataFrame."""
#     statement = select(Employees).where(Employees.usuario_id == usuario_id)
#     employees = session.exec(statement).all()

#     if not employees:
#         return pd.DataFrame()

#     data = []
#     for e in employees:
#         # Verificação robusta para dados None
#         nome = e.nome if e.nome else "Funcionário sem nome"
#         cargo = e.cargo if e.cargo else "Não informado"
#         salario = e.salario if e.salario is not None else 0.0
#         comissao = e.comissao if e.comissao is not None else 0.0
#         data_admissao = e.data_admissao if e.data_admissao else None

#         data.append({
#             "id": e.id,
#             "nome": nome,
#             "cargo": cargo,
#             "salario": salario,
#             "comissao": comissao,
#             "data_admissao": data_admissao,
#         })

#     return pd.DataFrame(data)

# # ===============================
# # Gerar indicadores
# # ===============================

# def generate_report(df_sales: pd.DataFrame, df_products: pd.DataFrame,
#                    df_customers: pd.DataFrame, df_employees: pd.DataFrame) -> dict:
#     report = {}

#     # Se não houver vendas
#     if df_sales.empty:
#         report.update({
#             "produto_mais_vendido": "Nenhum",
#             "produto_menos_vendido": "Nenhum",
#             "mes_mais_vendas": "Nenhum",
#             "dia_mais_vendas": "Nenhum",
#             "funcionario_mais_vendeu": "Nenhum",
#             "faturamento_total": 0.0,
#             "custo_total": 0.0,
#             "lucro_total": 0.0,
#             "lucro_percentual": 0.0,
#             "clientes_mais_compram": {},
#             "ticket_medio": 0.0,
#             "formas_pagamento_mais_usadas": {},
#             "vendas_semanal": {},
#             "vendas_mensal": {},
#             "total_vendas": 0,
#             "media_diaria_vendas": 0.0,
#             "crescimento_mensal": 0.0,
#         })
#     else:
#         # Garantir que as datas são timezone-aware
#         if 'criado_em' in df_sales.columns:
#             df_sales['criado_em'] = ensure_timezone_aware_series(df_sales['criado_em'])

#         # Produto mais e menos vendido
#         grouped_prod = df_sales.groupby("produto")["quantidade"].sum()
#         report["produto_mais_vendido"] = grouped_prod.idxmax() if not grouped_prod.empty else "Nenhum"
#         report["produto_menos_vendido"] = grouped_prod.idxmin() if not grouped_prod.empty else "Nenhum"

#         # Mês com mais vendas
#         df_sales["mes"] = df_sales["criado_em"].dt.to_period("M")
#         vendas_por_mes = df_sales.groupby("mes")["total_price"].sum()
#         report["mes_mais_vendas"] = vendas_por_mes.idxmax().strftime("%B %Y") if not vendas_por_mes.empty else "Nenhum"

#         # Dia com mais vendas
#         df_sales["dia"] = df_sales["criado_em"].dt.date
#         vendas_por_dia = df_sales.groupby("dia")["total_price"].sum()
#         report["dia_mais_vendas"] = vendas_por_dia.idxmax().strftime("%d/%m/%Y") if not vendas_por_dia.empty else "Nenhum"

#         # Funcionário que mais vendeu
#         grouped_func = df_sales.groupby("funcionario")["total_price"].sum()
#         report["funcionario_mais_vendeu"] = grouped_func.idxmax() if not grouped_func.empty else "Nenhum"

#         # Total faturamento, custo, lucro
#         report["faturamento_total"] = df_sales["total_price"].sum()
#         report["custo_total"] = df_sales["cost_price"].sum()
#         report["lucro_total"] = df_sales["lucro"].sum()

#         # Lucro percentual
#         if report["faturamento_total"] > 0:
#             report["lucro_percentual"] = (report["lucro_total"] / report["faturamento_total"]) * 100
#         else:
#             report["lucro_percentual"] = 0.0

#         # Clientes que mais compram
#         grouped_client = df_sales.groupby("cliente_nome")["total_price"].sum()
#         report["clientes_mais_compram"] = grouped_client.sort_values(ascending=False).head(5).to_dict() if not grouped_client.empty else {}

#         # Ticket médio
#         report["ticket_medio"] = df_sales["total_price"].mean() if not df_sales.empty else 0.0

#         # Formas de pagamento mais usadas
#         grouped_payment = df_sales.groupby("forma_pagamento")["total_price"].count()
#         report["formas_pagamento_mais_usadas"] = grouped_payment.sort_values(ascending=False).to_dict() if not grouped_payment.empty else {}

#         # Comparação semanal e mensal
#         df_sales["mes"] = df_sales["criado_em"].dt.tz_convert(None).dt.to_period("M")
#         df_sales["semana"] = df_sales["criado_em"].dt.tz_convert(None).dt.to_period("W").apply(lambda r: r.start_time.date())
#         report["vendas_semanal"] = df_sales.groupby("semana")["total_price"].sum().to_dict() if not df_sales.empty else {}
#         report["vendas_mensal"] = df_sales.groupby("mes")["total_price"].sum().to_dict() if not df_sales.empty else {}

#         # Total de vendas
#         report["total_vendas"] = len(df_sales)

#         # Média diária de vendas
#         dias_unico = df_sales["dia"].nunique()
#         report["media_diaria_vendas"] = report["total_vendas"] / dias_unico if dias_unico > 0 else 0

#         # Crescimento mensal (comparação com o mês anterior)
#         if len(vendas_por_mes) > 1:
#             ultimos_meses = vendas_por_mes.sort_index().tail(2)
#             if len(ultimos_meses) == 2:
#                 mes_atual = ultimos_meses.iloc[-1]
#                 mes_anterior = ultimos_meses.iloc[-2]
#                 if mes_anterior > 0:
#                     report["crescimento_mensal"] = ((mes_atual - mes_anterior) / mes_anterior) * 100
#                 else:
#                     report["crescimento_mensal"] = 100.0 if mes_atual > 0 else 0.0
#             else:
#                 report["crescimento_mensal"] = 0.0
#         else:
#             report["crescimento_mensal"] = 0.0

#     # Informações sobre produtos
#     if df_products.empty:
#         report["produtos_proximos_validade"] = []
#         report["produtos_estoque_baixo"] = []
#         report["produtos_estoque_alto"] = []
#         report["total_produtos"] = 0
#         report["valor_total_estoque"] = 0.0
#     else:
#         today = datetime.now(DEFAULT_TZ).date()

#         # Produtos próximos da validade (7 dias)
#         df_products["days_to_expire"] = df_products["date_expired"].apply(
#             lambda d: (d.date() - today).days if pd.notnull(d) and hasattr(d, 'date') else None
#         )
#         report["produtos_proximos_validade"] = df_products[
#             (df_products["days_to_expire"] <= 7) & (df_products["days_to_expire"] >= 0)
#         ]["nome"].tolist()

#         # Produtos com estoque baixo
#         report["produtos_estoque_baixo"] = df_products[
#             df_products["stock"] <= df_products["stoke_min"]
#         ]["nome"].tolist()

#         # Produtos com estoque alto
#         report["produtos_estoque_alto"] = df_products[
#             df_products["stock"] >= df_products["stoke_max"]
#         ]["nome"].tolist()

#         # Total de produtos
#         report["total_produtos"] = len(df_products)

#         # Valor total em estoque (estimativa)
#         report["valor_total_estoque"] = df_products["stock"].sum()

#     # Informações sobre clientes
#     if df_customers.empty:
#         report["total_clientes"] = 0
#         report["clientes_ativos"] = 0
#         report["clientes_inativos"] = 0
#         report["valor_medio_credito"] = 0.0
#         report["valor_total_credito"] = 0.0
#     else:
#         report["total_clientes"] = len(df_customers)
#         report["clientes_ativos"] = len(df_customers[df_customers["status"] == "Ativo"])
#         report["clientes_inativos"] = len(df_customers[df_customers["status"] != "Ativo"])
#         report["valor_medio_credito"] = df_customers["credit"].mean()
#         report["valor_total_credito"] = df_customers["credit"].sum()

#     # Informações sobre funcionários
#     if df_employees.empty:
#         report["total_funcionarios"] = 0
#         report["cargos_mais_comuns"] = {}
#         report["salario_medio"] = 0.0
#         report["comissao_media"] = 0.0
#     else:
#         report["total_funcionarios"] = len(df_employees)

#         # Cargos mais comuns
#         cargos_count = df_employees["cargo"].value_counts().to_dict()
#         report["cargos_mais_comuns"] = cargos_count

#         # Salário médio
#         report["salario_medio"] = df_employees["salario"].mean()

#         # Comissão média
#         report["comissao_media"] = df_employees["comissao"].mean()

#     return report

# # ===============================
# # Gerar gráficos
# # ===============================

# def plot_graphs(df_sales: pd.DataFrame, df_products: pd.DataFrame,
#                 df_customers: pd.DataFrame, df_employees: pd.DataFrame) -> Dict[str, str]:
#     """Gera gráficos e retorna os caminhos dos arquivos."""
#     graph_files = {}

#     # Gráfico 1: Top produtos vendidos (se houver vendas)
#     if not df_sales.empty:
#         try:
#             top_products = df_sales.groupby("produto")["quantidade"].sum().sort_values(ascending=False).head(5)
#             plt.figure(figsize=(10, 6))
#             bars = plt.bar(range(len(top_products)), top_products.values, color=COLORS)
#             plt.title("Top 5 Produtos Mais Vendidos", fontsize=14, fontweight='bold')
#             plt.ylabel("Quantidade Vendida", fontsize=12)
#             plt.xticks(range(len(top_products)), top_products.index, rotation=45, ha='right')

#             # Adicionar valores nas barras
#             for i, v in enumerate(top_products.values):
#                 plt.text(i, v + 0.1, str(v), ha='center', va='bottom')

#             plt.tight_layout()
#             plt.savefig("top_products.png", dpi=300, bbox_inches='tight')
#             graph_files["top_products"] = "top_products.png"
#             plt.close()
#         except Exception as e:
#             print(f"Erro ao gerar gráfico de top produtos: {e}")

#     # Gráfico 2: Vendas por funcionário (se houver vendas)
#     if not df_sales.empty:
#         try:
#             top_func = df_sales.groupby("funcionario")["total_price"].sum().sort_values(ascending=True).tail(10)
#             plt.figure(figsize=(10, 6))
#             bars = plt.barh(range(len(top_func)), top_func.values, color=COLORS)
#             plt.title("Vendas por Funcionário (Top 10)", fontsize=14, fontweight='bold')
#             plt.xlabel("Faturamento (R$)", fontsize=12)
#             plt.yticks(range(len(top_func)), top_func.index)

#             # Adicionar valores nas barras
#             for i, v in enumerate(top_func.values):
#                 plt.text(v + 0.1, i, f"R$ {v:.2f}", va='center')

#             plt.tight_layout()
#             plt.savefig("vendas_funcionarios.png", dpi=300, bbox_inches='tight')
#             graph_files["vendas_funcionarios"] = "vendas_funcionarios.png"
#             plt.close()
#         except Exception as e:
#             print(f"Erro ao gerar gráfico de vendas por funcionário: {e}")

#     # Gráfico 3: Distribuição de formas de pagamento (se houver vendas)
#     if not df_sales.empty:
#         try:
#             payment_dist = df_sales["forma_pagamento"].value_counts()
#             plt.figure(figsize=(8, 8))
#             plt.pie(payment_dist.values, labels=payment_dist.index, autopct='%1.1f%%',
#                     colors=COLORS, startangle=90)
#             plt.title("Distribuição de Formas de Pagamento", fontsize=14, fontweight='bold')
#             plt.tight_layout()
#             plt.savefig("formas_pagamento.png", dpi=300, bbox_inches='tight')
#             graph_files["formas_pagamento"] = "formas_pagamento.png"
#             plt.close()
#         except Exception as e:
#             print(f"Erro ao gerar gráfico de formas de pagamento: {e}")

#     # Gráfico 4: Evolução de vendas ao longo do tempo (se houver vendas suficientes)
#     if not df_sales.empty and len(df_sales) > 1:
#         try:
#             # Agrupar vendas por dia
#             df_sales_copy = df_sales.copy()
#             df_sales_copy['data'] = df_sales_copy['criado_em'].dt.date
#             vendas_por_dia = df_sales_copy.groupby('data')['total_price'].sum()

#             plt.figure(figsize=(12, 6))
#             plt.plot(vendas_por_dia.index, vendas_por_dia.values, marker='o', linewidth=2, markersize=4, color=COLORS[0])
#             plt.title("Evolução de Vendas Diárias", fontsize=14, fontweight='bold')
#             plt.xlabel("Data", fontsize=12)
#             plt.ylabel("Faturamento (R$)", fontsize=12)
#             plt.xticks(rotation=45)
#             plt.grid(True, alpha=0.3)
#             plt.tight_layout()
#             plt.savefig("evolucao_vendas.png", dpi=300, bbox_inches='tight')
#             graph_files["evolucao_vendas"] = "evolucao_vendas.png"
#             plt.close()
#         except Exception as e:
#             print(f"Erro ao gerar gráfico de evolução de vendas: {e}")

#     # Gráfico 5: Distribuição de estoque (se houver produtos)
#     if not df_products.empty:
#         try:
#             # Categorizar produtos por nível de estoque
#             baixo = len(df_products[df_products["stock"] <= df_products["stoke_min"]])
#             adequado = len(df_products[(df_products["stock"] > df_products["stoke_min"]) &
#                                      (df_products["stock"] < df_products["stoke_max"])])
#             alto = len(df_products[df_products["stock"] >= df_products["stoke_max"]])

#             labels = ['Estoque Baixo', 'Estoque Adequado', 'Estoque Alto']
#             sizes = [baixo, adequado, alto]
#             colors = ['#ff9999', '#66b3ff', '#99ff99']

#             plt.figure(figsize=(8, 8))
#             plt.pie(sizes, labels=labels, autopcept='%1.1f%%', colors=colors, startangle=90)
#             plt.title("Distribuição de Níveis de Estoque", fontsize=14, fontweight='bold')
#             plt.tight_layout()
#             plt.savefig("distribuicao_estoque.png", dpi=300, bbox_inches='tight')
#             graph_files["distribuicao_estoque"] = "distribuicao_estoque.png"
#             plt.close()
#         except Exception as e:
#             print(f"Erro ao gerar gráfico de distribuição de estoque: {e}")

#     return graph_files

# # ===============================
# # Gerar PDF
# # ===============================
# class PDFReport(FPDF):
#     """Classe personalizada para gerar relatórios PDF com suporte a UTF-8."""

#     def __init__(self, logo: str = None, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.logo = logo
#         self.set_auto_page_break(auto=True, margin=15)
#         self.add_page()

#     def header(self):
#         # Logo
#         if self.logo:
#             try:
#                 # Extrair a parte base64 da string
#                 if self.logo.startswith('data:image'):
#                     base64_data = self.logo.split(',')[1]
#                 else:
#                     base64_data = self.logo

#                 # Decodificar base64 para bytes
#                 image_data = base64.b64decode(base64_data)

#                 # Salvar temporariamente e carregar com PIL para obter dimensões
#                 with open("temp_logo.png", "wb") as f:
#                     f.write(image_data)

#                 img = Image.open("temp_logo.png")
#                 width, height = img.size

#                 # Calcular proporção para caber no espaço do cabeçalho
#                 max_width = 40
#                 max_height = 25
#                 ratio = min(max_width/width, max_height/height)
#                 new_width = width * ratio
#                 new_height = height * ratio

#                 # Inserir a imagem
#                 self.image("temp_logo.png", x=10, y=8, w=new_width, h=new_height)

#                 # Remover arquivo temporário
#                 if os.path.exists("temp_logo.png"):
#                     os.remove("temp_logo.png")
#             except Exception as e:
#                 print(f"Erro ao carregar logo: {e}")
#                 self.logo = None

#         # Título
#         self.set_font('Arial', 'B', 16)
#         self.cell(0, 10, 'Relatório PDV - Sistema de Gestão', 0, 1, 'C')
#         self.ln(5)

#     def footer(self):
#         # Posição a 1.5 cm do final
#         self.set_y(-15)
#         self.set_font('Arial', 'I', 8)
#         # Número de página
#         self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

#     def chapter_title(self, title):
#         self.set_font('Arial', 'B', 12)
#         self.set_fill_color(200, 220, 255)
#         self.cell(0, 6, title, 0, 1, 'L', 1)
#         self.ln(4)

#     def chapter_body(self, body):
#         self.set_font('Arial', '', 10)
#         # Escrever o texto justificado
#         self.multi_cell(0, 5, body)
#         self.ln()

#     def add_table(self, data, headers):
#         # Configurar cores e fontes para a tabela
#         self.set_fill_color(225, 225, 225)
#         self.set_text_color(0)
#         self.set_draw_color(0, 0, 0)
#         self.set_line_width(0.3)
#         self.set_font('Arial', 'B', 10)

#         # Largura das colunas
#         col_widths = [self.w / len(headers)] * len(headers)

#         # Cabeçalho da tabela
#         for i, header in enumerate(headers):
#             self.cell(col_widths[i], 7, header, 1, 0, 'C', 1)
#         self.ln()

#         # Dados da tabela
#         self.set_font('Arial', '', 10)
#         fill = False
#         for row in data:
#             for i, item in enumerate(row):
#                 # Converter para string e garantir encoding adequado
#                 cell_text = str(item) if item is not None else ""
#                 self.cell(col_widths[i], 6, cell_text, 'LR', 0, 'C', fill)
#             self.ln()
#             fill = not fill

#         # Fechar a tabela
#         self.cell(sum(col_widths), 0, '', 'T')
#         self.ln()

#     # Sobrescrever o método cell para lidar com Unicode
#     def cell(self, w, h=0, txt='', border=0, ln=0, align='', fill=False, link=''):
#         # Substituir caracteres problemáticos
#         if txt:
#             txt = self.sanitize_text(txt)
#         super().cell(w, h, txt, border, ln, align, fill, link)

#     # Sobrescrever o método multi_cell para lidar com Unicode
#     def multi_cell(self, w, h=0, txt='', border=0, align='J', fill=False):
#         # Substituir caracteres problemáticos
#         if txt:
#             txt = self.sanitize_text(txt)
#         super().multi_cell(w, h, txt, border, align, fill)

#     def sanitize_text(self, text):
#         """Substitui caracteres Unicode problemáticos por equivalentes ASCII."""
#         if not isinstance(text, str):
#             text = str(text)

#         replacements = {
#             '•': '-',       # Bullet point para hífen
#             '–': '-',       # En dash para hífen
#             '—': '-',       # Em dash para hífen
#             '“': '"',       # Aspas curvas para retas
#             '”': '"',
#             '‘': "'",
#             '’': "'",
#             '…': '...',     # Ellipsis
#             '€': 'EUR',     # Símbolo do Euro
#             '£': 'GBP',     # Símbolo da Libra
#             '¥': 'JPY',     # Símbolo do Yen
#             '°': ' graus',  # Grau
#             'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
#             'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
#             'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
#             'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
#             'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
#             'ç': 'c',
#             'Á': 'A', 'À': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A',
#             'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
#             'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
#             'Ó': 'O', 'Ò': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O',
#             'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
#             'Ç': 'C'
#         }

#         for char, replacement in replacements.items():
#             text = text.replace(char, replacement)

#         return text

# def create_pdf(report: dict, usuario: Usuario, graph_files: dict, logo: str = None) -> str:
#     """Cria um relatório PDF completo."""
#     pdf = PDFReport(logo=logo)
#     pdf.alias_nb_pages()

#     # Informações da empresa
#     pdf.set_font('Arial', 'B', 14)
#     pdf.cell(0, 10, usuario.company_name, 0, 1, 'C')
#     pdf.set_font('Arial', '', 10)
#     if usuario.trade_name:
#         pdf.cell(0, 6, f"Nome Fantasia: {usuario.trade_name}", 0, 1, 'C')
#     pdf.cell(0, 6, f"Data do Relatório: {datetime.now(DEFAULT_TZ).strftime('%d/%m/%Y %H:%M')}", 0, 1, 'C')
#     pdf.ln(10)

#     # Resumo executivo
#     pdf.chapter_title("RESUMO EXECUTIVO")

#     resumo_text = f"""
#     Este relatório apresenta uma análise completa das operações do PDV. No período analisado,
#     foram realizadas {report['total_vendas']} vendas, totalizando um faturamento de R$ {report['faturamento_total']:.2f}.

#     O lucro obtido foi de R$ {report['lucro_total']:.2f}, representando {report['lucro_percentual']:.2f}% do faturamento.
#     O ticket médio foi de R$ {report['ticket_medio']:.2f} por venda.

#     O crescimento mensal foi de {report['crescimento_mensal']:.2f}% em relação ao mês anterior.
#     """
#     pdf.chapter_body(resumo_text)
#     pdf.ln(5)

#     # Métricas principais em formato de tabela
#     pdf.chapter_title("MÉTRICAS PRINCIPAIS")

#     metrics_data = [
#         ["Faturamento Total", f"R$ {report['faturamento_total']:.2f}"],
#         ["Custo Total", f"R$ {report['custo_total']:.2f}"],
#         ["Lucro Total", f"R$ {report['lucro_total']:.2f}"],
#         ["Lucro Percentual", f"{report['lucro_percentual']:.2f}%"],
#         ["Ticket Médio", f"R$ {report['ticket_medio']:.2f}"],
#         ["Total de Vendas", report['total_vendas']],
#         ["Média Diária de Vendas", f"{report['media_diaria_vendas']:.2f}"],
#         ["Crescimento Mensal", f"{report['crescimento_mensal']:.2f}%"]
#     ]

#     pdf.add_table(metrics_data, ["Métrica", "Valor"])
#     pdf.ln(10)

#     # Informações sobre produtos
#     pdf.chapter_title("INFORMAÇÕES SOBRE PRODUTOS")

#     produtos_text = f"""
#     Total de produtos cadastrados: {report['total_produtos']}
#     Valor total estimado em estoque: R$ {report['valor_total_estoque']:.2f}

#     Produtos com estoque baixo: {len(report['produtos_estoque_baixo'])}
#     Produtos com estoque alto: {len(report['produtos_estoque_alto'])}
#     Produtos próximos da validade: {len(report['produtos_proximos_validade'])}

#     Produto mais vendido: {report['produto_mais_vendido']}
#     Produto menos vendido: {report['produto_menos_vendido']}
#     """
#     pdf.chapter_body(produtos_text)

#     # Lista de produtos com estoque baixo
#     if report['produtos_estoque_baixo']:
#         pdf.set_font('Arial', 'B', 10)
#         pdf.cell(0, 6, "Produtos com estoque baixo:", 0, 1)
#         pdf.set_font('Arial', '', 10)
#         for produto in report['produtos_estoque_baixo']:
#             pdf.cell(0, 5, f"- {produto}", 0, 1)  # Usando hífen em vez de bullet
#         pdf.ln(3)

#     # Lista de produtos próximos da validade
#     if report['produtos_proximos_validade']:
#         pdf.set_font('Arial', 'B', 10)
#         pdf.cell(0, 6, "Produtos próximos da validade:", 0, 1)
#         pdf.set_font('Arial', '', 10)
#         for produto in report['produtos_proximos_validade']:
#             pdf.cell(0, 5, f"- {produto}", 0, 1)  # Usando hífen em vez de bullet
#         pdf.ln(3)

#     pdf.ln(5)

#     # Informações sobre clientes
#     pdf.chapter_title("INFORMAÇÕES SOBRE CLIENTES")

#     clientes_text = f"""
#     Total de clientes cadastrados: {report['total_clientes']}
#     Clientes ativos: {report['clientes_ativos']}
#     Clientes inativos: {report['clientes_inativos']}

#     Valor médio de crédito: R$ {report['valor_medio_credito']:.2f}
#     Valor total de crédito: R$ {report['valor_total_credito']:.2f}
#     """
#     pdf.chapter_body(clientes_text)

#     # Top clientes
#     if report['clientes_mais_compram']:
#         pdf.set_font('Arial', 'B', 10)
#         pdf.cell(0, 6, "Top 5 clientes que mais compram:", 0, 1)
#         pdf.set_font('Arial', '', 10)
#         clientes_data = []
#         for cliente, valor in report['clientes_mais_compram'].items():
#             clientes_data.append([cliente, f"R$ {valor:.2f}"])

#         pdf.add_table(clientes_data, ["Cliente", "Valor Gasto"])
#         pdf.ln(5)

#     # Informações sobre funcionários
#     pdf.chapter_title("INFORMAÇÕES SOBRE FUNCIONÁRIOS")

#     funcionarios_text = f"""
#     Total de funcionários: {report['total_funcionarios']}
#     Salário médio: R$ {report['salario_medio']:.2f}
#     Comissão média: {report['comissao_media']:.2f}%

#     Funcionário que mais vendeu: {report['funcionario_mais_vendeu']}
#     """
#     pdf.chapter_body(funcionarios_text)

#     # Cargos mais comuns
#     if report['cargos_mais_comuns']:
#         pdf.set_font('Arial', 'B', 10)
#         pdf.cell(0, 6, "Distribuição de cargos:", 0, 1)
#         pdf.set_font('Arial', '', 10)
#         cargos_data = []
#         for cargo, quantidade in report['cargos_mais_comuns'].items():
#             cargos_data.append([cargo, quantidade])

#         pdf.add_table(cargos_data, ["Cargo", "Quantidade"])
#         pdf.ln(5)

#     # Formas de pagamento
#     pdf.chapter_title("FORMAS DE PAGAMENTO")

#     if report['formas_pagamento_mais_usadas']:
#         pagamentos_data = []
#         for forma, quantidade in report['formas_pagamento_mais_usadas'].items():
#             pagamentos_data.append([forma, quantidade])

#         pdf.add_table(pagamentos_data, ["Forma de Pagamento", "Quantidade"])
#         pdf.ln(5)

#     # Adicionar gráficos
#     if graph_files:
#         pdf.add_page()
#         pdf.chapter_title("GRÁFICOS E VISUALIZAÇÕES")

#         # Top produtos
#         if "top_products" in graph_files:
#             pdf.set_font('Arial', 'B', 10)
#             pdf.cell(0, 6, "Top 5 Produtos Mais Vendidos", 0, 1)
#             pdf.image(graph_files["top_products"], x=10, w=190)
#             pdf.ln(5)

#         # Vendas por funcionário
#         if "vendas_funcionarios" in graph_files:
#             pdf.set_font('Arial', 'B', 10)
#             pdf.cell(0, 6, "Vendas por Funcionário (Top 10)", 0, 1)
#             pdf.image(graph_files["vendas_funcionarios"], x=10, w=190)
#             pdf.ln(5)

#         # Formas de pagamento
#         if "formas_pagamento" in graph_files:
#             pdf.set_font('Arial', 'B', 10)
#             pdf.cell(0, 6, "Distribuição de Formas de Pagamento", 0, 1)
#             pdf.image(graph_files["formas_pagamento"], x=10, w=190)
#             pdf.ln(5)

#         # Evolução de vendas
#         if "evolucao_vendas" in graph_files:
#             pdf.set_font('Arial', 'B', 10)
#             pdf.cell(0, 6, "Evolução de Vendas Diárias", 0, 1)
#             pdf.image(graph_files["evolucao_vendas"], x=10, w=190)
#             pdf.ln(5)

#         # Distribuição de estoque
#         if "distribuicao_estoque" in graph_files:
#             pdf.set_font('Arial', 'B', 10)
#             pdf.cell(0, 6, "Distribuição de Níveis de Estoque", 0, 1)
#             pdf.image(graph_files["distribuicao_estoque"], x=10, w=190)
#             pdf.ln(5)

#     # Gerar nome do arquivo
#     pdf_file = f"relatorio_{usuario.company_name}_{datetime.now(DEFAULT_TZ).strftime('%Y%m%d_%H%M%S')}.pdf"
#     pdf.output(pdf_file)

#     return pdf_file

# # ===============================
# # Função principal para rota
# # ===============================

# def generate_report_pdv(
#     session: Session,
#     start_date: date = None,
#     end_date: date = None,
#     logo_path: str = None,
#     logo_base64: str = None
# ) -> FileResponse:
#     """
#     Gera um relatório PDV completo para o usuário especificado.

#     Args:
#         session: Sessão do banco de dados
#         usuario_id: ID do usuário
#         start_date: Data inicial para o relatório (opcional)
#         end_date: Data final para o relatório (opcional)
#         logo_path: Caminho para o arquivo de logo (opcional)
#         logo_base64: String base64 da logo (opcional)

#     Returns:
#         FileResponse: Relatório PDF
#     """
#     try:
#         # Carregar dados do usuário
#         usuario = session.get(Usuario, usuario_id)
#         if not usuario:
#             raise ValueError("Usuário não encontrado")

#         # Carregar logo
#         logo = load_logo(logo_path, logo_base64)

#         # Buscar dados
#         df_sales = fetch_sales_data(session, usuario_id, start_date, end_date)
#         df_products = fetch_products_data(session, usuario_id)
#         df_customers = fetch_customers_data(session, usuario_id)
#         df_employees = fetch_employees_data(session, usuario_id)

#         # Gerar relatório
#         report = generate_report(df_sales, df_products, df_customers, df_employees)

#         # Gerar gráficos
#         graph_files = plot_graphs(df_sales, df_products, df_customers, df_employees)

#         # Criar PDF
#         pdf_file = create_pdf(report, usuario, graph_files, logo)

#         # Limpar arquivos temporários
#         for file_path in graph_files.values():
#             if os.path.exists(file_path):
#                 os.remove(file_path)

#         return FileResponse(
#             pdf_file,
#             filename=pdf_file,
#             media_type='application/pdf',
#             headers={"Content-Disposition": f"attachment; filename={pdf_file}"}
#         )

#     except Exception as e:
#         # Em caso de erro, criar um PDF de erro
#         error_pdf = FPDF()
#         error_pdf.add_page()
#         error_pdf.set_font('Arial', 'B', 16)
#         error_pdf.cell(0, 10, 'Erro ao Gerar Relatório', 0, 1, 'C')
#         error_pdf.set_font('Arial', '', 12)
#         error_pdf.multi_cell(0, 10, f'Ocorreu um erro ao gerar o relatório: {str(e)}')

#         error_file = f"erro_relatorio_{datetime.now(DEFAULT_TZ).strftime('%Y%m%d_%H%M%S')}.pdf"
#         error_pdf.output(error_file)

#         return FileResponse(
#             error_file,
#             filename=error_file,
#             media_type='application/pdf'
#         )
