import flet as ft
import subprocess
import os
import sys
import time
import asyncio

# --- CONFIGURAÇÃO ---
GRUPO_ATIVO = 20  # Mude aqui de 1 a 17 para cada aplicativo
LOJA= "Nova Cintra"
# Mapeamento dos PDVs (4 a 6 itens)
# Formato: "Nome do Botão": "Final do IP"
DADOS_PDV = {
    "PDV-101": "1",
    "PDV-102": "2",
    "PDV-103": "3",
    "PDV-104": "4",
    "PDV-105": "5",
    #"PDV-106": "6"
}

# Gera a lista de IPs automaticamente com base no grupo
# Ex: Se GRUPO_ATIVO = 2, o primeiro IP será 10.28.2.1
LISTA_TERMINAIS = [
    {"label": nome, "ip": f"10.28.{GRUPO_ATIVO}.{final_ip}"} 
    for nome, final_ip in DADOS_PDV.items()
]

TITULO_APP = f"Painel PDV - Loja {LOJA} {GRUPO_ATIVO:02d}"
#LISTA_DE_IPS = ["192.168.1.10", "192.168.1.11", "192.168.1.12", "192.168.1.13", "192.168.1.14", "192.168.1.15"]


# Localiza o PsExec dentro do EXE portátil
def obter_caminho_recurso(nome_arquivo):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, nome_arquivo)
    return os.path.join(os.path.abspath("."), nome_arquivo)

CAMINHO_PSEXEC = obter_caminho_recurso("psexec.exe")


async def main(page: ft.Page):
    # 1. Diz para o Flet: "Quando clicarem no X, avise a gente antes de fechar"
    page.window_prevent_close = True 
    # Guardará tuplas: (ip_real, objeto_botao)
    botoes_para_monitorar = []
    # para fazer a janela fechar pelo X
    async def evento_janela(e):
        if e.data == "close":
            page.window_destroy() # Fecha a janela visual
            sys.exit() # Mata o processo Python imediatamente
    page.window.on_event = evento_janela
    ##
    
    async def monitorar_rede():
        
        while True:
            
            # Percorre a lista que populamos na função main
            for ip, btn in botoes_para_monitorar:
                try:
                    # O comando exato: ir no host e pedir o hostname
                    comando = ["psexec.exe", "-n", "2", f"\\\\{ip}", "hostname"]
                    
                    # Executa o ping
                    processo = await asyncio.to_thread(
                        subprocess.run,
                        comando,
                        creationflags=subprocess.HIGH_PRIORITY_CLASS | subprocess.CREATE_NO_WINDOW,
                        capture_output=True,
                        timeout=3 # 3 segundos para responder
                    )
    
                    # Acessa o Ícone (que é o item 0 da Row dentro do botão)
                    icone = btn.content.controls[0]
                    
                    if processo.returncode == 0:
                        # UP (Verde)
                        btn.style.bgcolor = ft.Colors.GREEN_400
                        #icone.color = ft.Colors.GREEN
                        print(f"UP{ip}")
                    else:
                        # DOWN (Preto - Falha na conexão ou erro)
                        #icone.color = ft.Colors.BLACK
                        btn.style.bgcolor = ft.Colors.GREY
                        print(f"DOWM{ip}")
    
                    # Atualiza o visual do botão
                    #btn.update()
    
                except Exception:
                    btn.style.bgcolor = ft.Colors.GREY
                    print(f"EXC{ip}")
                    # Se der erro no script ou algo muito estranho, mantém/volta para Unknown
                    # Ou se preferir que Timeout seja Preto, mova para o 'else' acima.
                    #try:
                    #    btn.content.controls[0].color = ft.Colors.BLACK 
                    #    btn.update()
                    #except:
                    #    pass # Se o botão não existir mais
    
                # Pausa de 0.5s entre um host e outro para não travar a rede
                #await asyncio.sleep(0.1)
            page.update()
    
            # Espera 30 segundos antes de escanear todos novamente
            await asyncio.sleep(30)
        
    page.title = f"Gerenciar PDVs - Loja {LOJA} {GRUPO_ATIVO:02d}"
    page.window.width = 550
    page.window.height = 600
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 30
    fila = asyncio.Queue()

        
    async def processar_fila():
        while True:
            ip_alvo, nome, btn, conteudo_original,tipo = await fila.get()
            if tipo == "DESLIGAR":
                flag_acao = "-s"
                texto_acao = "Desligando"
            else: # Se for REINICIAR ou qualquer outra coisa
                flag_acao = "-r"
                texto_acao = "Reiniciando"
            try:
                comando = [
                    "psexec.exe", "-accepteula", "-n", "2", 
                    f"\\\\{ip_alvo}", "shutdown", flag_acao, "-f", "-t", "5"
                ]
                
                flags = subprocess.HIGH_PRIORITY_CLASS | subprocess.CREATE_NO_WINDOW
                
                resultado = await asyncio.to_thread(
                    subprocess.run, 
                    comando, 
                    creationflags=flags,
                    timeout=5,
                    #capture_output=True, 
                    #text=True            
                )
                if resultado.returncode == 0:
                    msg, cor = f"{texto_acao}: {nome}", "green"
                else:
                    msg, cor = f"Falhou, (Erro {resultado.returncode}): {nome}", "red"
            
            except Exception:
                msg, cor = f"Excecao", "red"
    
            page.overlay.append(ft.SnackBar(ft.Text(msg), bgcolor=cor, open=True))
            
            btn.content = conteudo_original
            btn.disabled = False
            page.update()
    async def abrir_menu_acao(e, ip_alvo, nome):
        btn = e.control
        conteudo_original = btn.content
        
        # Função para fechar (usa o novo método close do page)
        async def fechar(e_click):
            page.pop_dialog()

        # Função de confirmação
        async def confirmar(e_click):
            tipo = e_click.control.data
            page.pop_dialog()
            btn.content = ft.Row(
                [
                    ft.Text("🖥️", size=30),
                    ft.Text("Enviando...", weight="bold", size=16),
                ],
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
            )
            btn.disabled = True
            btn.update()
            await fila.put((ip_alvo, nome, btn, conteudo_original, tipo))
            #await executar_comando(e, ip, nome, tipo)
            #await fila.put((ip, nome, btn, conteudo_original, tipo))

        # O Novo Padrão de Diálogo (Material 3)
        dlg = ft.AlertDialog(
            title=ft.Text(f"Gerenciar {nome}"),
            content=ft.Text("Selecione a ação:"),
            actions=[
                ft.Column(
                    [
                        # Linha 1: Botões principais lado a lado
                        ft.Row(
                            [# TextButton: O ideal para "Cancelar" (sem cor de fundo)
                            
                                ##ft.TextButton("Cancelar", on_click=fechar),
                                
                                # FilledButton: O substituto moderno para botões com cor de fundo
                                ft.FilledButton(
                                    "Desligar 🛑", 
                                    data="DESLIGAR", 
                                    on_click=confirmar,
                                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700)
                                ),
                
                                ft.FilledButton(
                                    "Reiniciar 🔄", 
                                    data="REINICIAR", 
                                    on_click=confirmar,
                                    style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_700)
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER, # Centraliza os botões
                        ),
                        # Linha 2: Botão Cancelar abaixo
                        ft.Container(
                            content=ft.TextButton("Cancelar", on_click=fechar),
                            #alignment=ft.MainAxisAlignment.CENTER # Centraliza o cancelar
                            alignment=ft.Alignment(0, 0)
                        )
                    ],
                    tight=True, # IMPORTANTE: Faz a coluna ocupar só o espaço necessário
                )
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        page.show_dialog(dlg)
    
        
    # --- MONTAGEM DA INTERFACE ---
    # Layout de grade (lado a lado)
    grade = ft.Row(
        wrap=True,
        spacing=15,
        run_spacing=15,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    
    # JEITO CERTO (Cria um NOVO texto para cada botão dentro do loop)
    for item in LISTA_TERMINAIS:
        nome_exibicao = item["label"]
        ip_real = item["ip"]

           # 1. Crie o objeto de texto de forma ÚNICA para este loop
        texto_pdv = ft.Text(nome_exibicao, weight="bold", size=16)
        
        botao = ft.Button(
            content=ft.Row(
                [
                    ft.Text("🖥️", size=30),
                    texto_pdv, # Usamos a referência única
                ],
                tight=True, # Mantém ícone e texto grudados
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            width=220,
            height=60,
            on_click=lambda e, ip=ip_real,nome=nome_exibicao: page.run_task(abrir_menu_acao, e, ip, nome),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                # TROQUE ft.alignment.center POR ESTA LINHA ABAIXO:
                #alignment=ft.Alignment(0, 0), # 0,0 é o centro exato
            )
        )
        botoes_para_monitorar.append((ip_real, botao))
        grade.controls.append(botao)
    
    # Conteúdo da Página
    page.add(
        ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                # Tenta carregar a imagem, se não existir, apenas pula
                ft.Image(src="pdv.png", width=120, height=120, error_content=ft.Text("🛒", size=80)),
                ft.Text(f"Lista de PDVs - {LOJA}", size=22, weight="bold"),
                ft.Divider(height=20, color="transparent"),
                grade
            ]
        )
    )
    page.run_task(processar_fila)
    page.run_task(monitorar_rede)
if __name__ == "__main__":
    ft.run(main)
