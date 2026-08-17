#========================================================================================================================================================
#   Este Script executa a instalação de uma Máquina Virtual do TwinCat BSD.
#
# Requisitos:
#   Oracle VitualBox Gerenciador => https://download.virtualbox.org/virtualbox/7.2.12/Oracle_VirtualBox_Extension_Pack-7.2.12.vbox-extpack
#   imagem.iso => https://www.beckhoff.com/en-en/download/586494816

#   Guia de instalação após a execução deste script => https://infosys.beckhoff.com/english.php?content=../content/1033/twincat_bsd/14863432715.html&id=
#
#   Autor: Rosimar Lima
#   ùtima revisão: 2024-06-19
#
#========================================================================================================================================================

import os
import subprocess
import sys
import shutil
import time

# =========================================================
# Funções utilitárias
# =========================================================

def localizar_vboxmanage():
    """
    Localiza o executável VBoxManage.exe nos caminhos conhecidos.
    Retorna o caminho completo se encontrado, caso contrário encerra o programa.
    """
    caminhos = [
        r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe",
    ]

    for caminho in caminhos:
        if os.path.exists(caminho):
            return caminho

    print("VBoxManage.exe não encontrado nos caminhos padrão.")
    sys.exit(1)


def run(cmd):
    """
    Executa um comando no sistema e exibe o que está sendo executado.
    Se o comando falhar, o script é interrompido automaticamente.
    """
    print("Executando:", " ".join(cmd))
    subprocess.run(cmd, check=True)

def vm_existe(vboxmanage, nome_vm):
    resultado = subprocess.run(
        [vboxmanage, "list", "vms"],
        capture_output=True,
        text=True
    )

    for linha in resultado.stdout.splitlines():
        if linha.startswith(f'"{nome_vm}"'):
            return True

    return False


# =========================================================
# Remoção automática da VM existente
# =========================================================

def remover_vm_existente(vboxmanage, vmname, working_dir):

    if vm_existe(vboxmanage, vmname):

        print(f"VM '{vmname}' encontrada. Removendo...")

        try:
            subprocess.run(
                [vboxmanage, "controlvm", vmname, "poweroff"],
                capture_output=True,
                text=True
            )
            time.sleep(2)

        except Exception:
            pass

        run([
            vboxmanage,
            "unregistervm",
            vmname,
            "--delete"
        ])

    # Remove pasta mesmo se a VM não estiver registrada
    vm_dir = os.path.join(working_dir, vmname)

    if os.path.exists(vm_dir):

        print(f"Removendo diretório órfão: {vm_dir}")

        shutil.rmtree(
            vm_dir,
            ignore_errors=True
        )

        print("Diretório removido.")

    print("Limpeza concluída.\n")

# =========================================================
# Entrada do usuário
# =========================================================

def obter_nome_vm():
    """
    Solicita ao usuario o nome da VM.
    Apenas valida se não está vazio
    """

    while True:
        nome = input("Digite o nome da VM: ").strip()

        if not nome:
            print("O nome da VM não pode estar vazio.\n")
            continue
            
        return nome

   
# =========================================================
# Preparação de caminhos e arquivos
# =========================================================

def validar_iso(path_iso):
    """
    Verifica se a imagem ISO existe no caminho informado.
    """
    if not os.path.exists(path_iso):
        print(f"A imagem ISO não foi encontrada em:\n{path_iso}")
        sys.exit(1)


def preparar_diretorios(base_dir, vmname):
    """
    Cria o diretório da VM e define caminhos dos discos.
    """
    vm_dir = os.path.join(base_dir, vmname)
    os.makedirs(vm_dir, exist_ok=True)

    installer_vdi = os.path.join(vm_dir, "TcBSD_installer.vdi")
    runtime_vhd = os.path.join(vm_dir, "TcBSD.vhd")

    return vm_dir, installer_vdi, runtime_vhd


# =========================================================
# Criação da VM
# =========================================================

def criar_vm(vboxmanage, vmname, basefolder):
    """
    Cria e registra a VM no VirtualBox.
    """
    run([
        vboxmanage, "createvm",
        "--name", vmname,
        "--basefolder", basefolder,
        "--ostype", "FreeBSD_64",
        "--register"
    ])

    run([
        vboxmanage, "modifyvm", vmname,
        "--nic1", "hostonly",
        "--hostonlyadapter1", "VirtualBox Host-Only Ethernet Adapter",
        "--memory", "4096",
        "--vram", "128",
        "--acpi", "on",
        "--hpet", "on",
        "--graphicscontroller", "vmsvga",
        "--firmware", "efi64"
    ])


def preparar_discos(vboxmanage, iso_path, installer_vdi, runtime_vhd):
    """
    Converte a ISO para VDI e cria o disco de runtime em VHD.
    """
    run([
        vboxmanage, "convertfromraw",
        "--format", "VDI",
        iso_path,
        installer_vdi
    ])

    run([
        vboxmanage, "createmedium",
        "--filename", runtime_vhd,
        "--size", "20480",
        "--format", "VHD"
    ])


def configurar_storage(vboxmanage, vmname, installer_vdi, runtime_vhd):
    """
    Cria o controlador SATA e anexa os discos à VM.
    """
    run([
        vboxmanage, "storagectl", vmname,
        "--name", "SATA",
        "--add", "sata",
        "--controller", "IntelAhci",
        "--hostiocache", "on",
        "--bootable", "on"
    ])

    run([
        vboxmanage, "storageattach", vmname,
        "--storagectl", "SATA",
        "--device", "0",
        "--port", "1",
        "--type", "hdd",
        "--medium", installer_vdi
    ])

    run([
        vboxmanage, "storageattach", vmname,
        "--storagectl", "SATA",
        "--device", "0",
        "--port", "0",
        "--type", "hdd",
        "--medium", runtime_vhd
    ])


def iniciar_vm(vboxmanage, vmname):
    """
    Inicia a VM e aguarda ela entrar em execução.
    """

    run([
        vboxmanage,
        "startvm",
        vmname,
        "--type",
        "gui"
    ])

    aguardar_estado_vm(
        vboxmanage,
        vmname,
        "running",
        timeout=60
    )

def obter_estado_vm(vboxmanage, vmname):

    resultado = subprocess.run(
        [vboxmanage, "showvminfo", vmname, "--machinereadable"],
        capture_output=True,
        text=True,
        check=True
    )

    for linha in resultado.stdout.splitlines():

        if linha.startswith("VMState="):
            return linha.split("=")[1].strip('"')

    return None


def aguardar_estado_vm(
    vboxmanage,
    vmname,
    estado,
    timeout=120
):

    inicio = time.time()

    while time.time() - inicio < timeout:

        estado_atual = obter_estado_vm(
            vboxmanage,
            vmname
        )

        if estado_atual == estado:
            return

        time.sleep(1)

    raise TimeoutError(
        f"Estado '{estado}' não atingido."
    )


def aguardar_desligamento(
    vboxmanage,
    vmname,
    timeout=1800
):

    inicio = time.time()

    while time.time() - inicio < timeout:

        estado = obter_estado_vm(
            vboxmanage,
            vmname
        )

        if estado == "poweroff":
            return

        time.sleep(5)

    raise TimeoutError(
        "A VM não desligou dentro do tempo esperado."
    )


# =========================================================
# Fluxo principal
# =========================================================

def main():
    VBoxManage = localizar_vboxmanage()
    vmname = obter_nome_vm()
    working_dir = os.getcwd()

    # Se existir uma VM com o mesmo nome, remove completamente antes de criar uma nova
    remover_vm_existente(VBoxManage, vmname, working_dir)

    iso_path = r"C:\Users\rosim\OneDrive\PLC\TCBSD_X64\TCBSD-x64-14-334630.iso"
    validar_iso(iso_path)

    vm_dir, installer_vdi, runtime_vhd = preparar_diretorios(working_dir, vmname)

    criar_vm(VBoxManage, vmname, working_dir)
    preparar_discos(VBoxManage, iso_path, installer_vdi, runtime_vhd)
    configurar_storage(VBoxManage, vmname, installer_vdi, runtime_vhd)
    iniciar_vm(VBoxManage, vmname)

    print("Instalação Automática em andamento...")

    instalar_tcbsd(VBoxManage, vmname)   

def send_scancode(vboxmanage, vmname, *codes):
    subprocess.run(
        [vboxmanage, "controlvm", vmname,
         "keyboardputscancode", *codes],
        check=True
    )
def send_text(vboxmanage, vmname, texto):
    subprocess.run(
        [
            vboxmanage,
            "controlvm",
            vmname,
            "keyboardputstring",
            texto
        ],
        check=True
    )

def instalar_tcbsd(vboxmanage, vmname):

    print("Aguardando boot do instalador...")
    time.sleep(30)
    # =====================================================
    # Tela inicial
    # =====================================================
    print("Tela inicial")
    send_scancode(vboxmanage, vmname, "1c", "9c")
    time.sleep(2)

    # =====================================================
    # Disk Selection
    # =====================================================
    print("Selecionando disco")
    send_scancode(vboxmanage, vmname, "1c", "9c")
    time.sleep(2)

    # =====================================================
    # Warning -> YES
    # =====================================================
    print("Selecionando YES")

    # TAB para sair de NO e ir para YES
    send_scancode(vboxmanage, vmname, "0f", "8f")

    time.sleep(1)

    # ENTER
    send_scancode(vboxmanage, vmname, "1c", "9c")

    time.sleep(2)

    # =====================================================
    # Senha
    # =====================================================
    print("Definindo senha")

    send_text(vboxmanage, vmname, "1")

    time.sleep(1)

    # TAB para botão OK
    send_scancode(vboxmanage, vmname, "0f", "8f")

    time.sleep(1)

    # ENTER em OK
    send_scancode(vboxmanage, vmname, "1c", "9c")

    time.sleep(1)

    # =====================================================
    # Confirmar senha
    # =====================================================
    print("Confirmando senha")

    send_text(vboxmanage, vmname, "1")

    time.sleep(1)

    # TAB para botão OK
    send_scancode(vboxmanage, vmname, "0f", "8f")

    time.sleep(1)

    # ENTER em OK
    send_scancode(vboxmanage, vmname, "1c", "9c")

    # =====================================================
    # Aguarda instalação
    # =====================================================
        
    print("Instalação em andamento...")

    tempo_total = 175

    for segundos in range(tempo_total):

        percentual = int(((segundos + 1) / tempo_total) * 100)

        restante = tempo_total - segundos - 1

        minutos = restante // 60
        segundos_restantes = restante % 60

        barras = int(percentual / 2)

        barra = "█" * barras + "-" * (50 - barras)

        print(
        f"\r[{barra}] {percentual}% | Restante: {minutos:02d}:{segundos_restantes:02d}",
        end="",
        flush=True
        )

        time.sleep(1)

        
    # =====================================================
    # Instalação Completa
    # =====================================================
    print("Instalação concluída, confirmando...")

    send_scancode(vboxmanage, vmname, "1c", "9c")

    time.sleep(2)

    # =====================================================
    # Selecionar Shutdown
    # =====================================================
    print("Selecionando Shutdown")

    for _ in range(5):
        send_scancode(vboxmanage, vmname, "50", "d0")
        time.sleep(0.2)

    send_scancode(vboxmanage, vmname, "1c", "9c")
    print("Aguardando desligamento da VM...")
    time.sleep(8)

    print("Processo finalizado.")
    
if __name__ == "__main__":
    main()
