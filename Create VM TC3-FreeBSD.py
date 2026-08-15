#========================================================================================================================================================
#   Este Script executa a instalação de uma Máquina Virtual do TwinCat BSD.
#
# Requisitos:
#   Oracle VitualBox Gerenciador => https://download.virtualbox.org/virtualbox/7.2.12/Oracle_VirtualBox_Extension_Pack-7.2.12.vbox-extpack
#   imagem.iso => https://www.beckhoff.com/en-en/download/586494816
#   Guia de instalação após a execução deste script => https://infosys.beckhoff.com/english.php?content=../content/1033/twincat_bsd/14863432715.html&id=
#
#   Autor: Rosimar Lima
#========================================================================================================================================================

import os
import subprocess
import sys
import shutil

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
    """
    Verifica se uma VM com o nome especificado já existe no VirtualBox.
    Retorna True se existir, False caso contrário.
    """
    resultado = subprocess.run(
        [vboxmanage, "list", "vms"],
        capture_output=True,
        text=True
    )
    return nome_vm in resultado.stdout


# =========================================================
# Remoção automática da VM existente
# =========================================================

def remover_vm_existente(vboxmanage, vmname, working_dir):
    """
    Remove completamente uma VM existente:
    - Desregistra a VM do VirtualBox
    - Deleta discos e arquivos associados
    - Remove o diretório da VM no sistema de arquivos
    """
    if not vm_existe(vboxmanage, vmname):
        return  # Nada a remover

    print(f"⚠️ A VM '{vmname}' já existe. Removendo completamente...")

    # 1. Desregistrar e deletar discos
    run([
        vboxmanage, "unregistervm", vmname, "--delete"
    ])

    # 2. Remover diretório da VM
    vm_dir = os.path.join(working_dir, vmname)
    if os.path.exists(vm_dir):
        shutil.rmtree(vm_dir, ignore_errors=True)
        print(f"🗑️ Diretório removido: {vm_dir}")

    print(f"✅ VM '{vmname}' removida com sucesso.\n")


# =========================================================
# Entrada do usuário
# =========================================================

def obter_nome_vm():
    """
    Solicita ao usuário o nome da VM e valida que não esteja vazio.
    """
    nome = input("Digite o nome da VM: ").strip()
    if not nome:
        print("O nome da VM não pode estar vazio.")
        sys.exit(1)
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
    Inicia a VM em modo gráfico.
    """
    run([vboxmanage, "startvm", vmname, "--type", "gui"])


# =========================================================
# Fluxo principal
# =========================================================

def main():
    VBoxManage = localizar_vboxmanage()
    vmname = obter_nome_vm()
    working_dir = os.getcwd()

    # Remoção automática da VM existente
    remover_vm_existente(VBoxManage, vmname, working_dir)

    iso_path = r"C:\Users\rosim\OneDrive\PLC\TCBSD_X64\TCBSD-x64-14-334630.iso"
    validar_iso(iso_path)

    vm_dir, installer_vdi, runtime_vhd = preparar_diretorios(working_dir, vmname)

    criar_vm(VBoxManage, vmname, working_dir)
    preparar_discos(VBoxManage, iso_path, installer_vdi, runtime_vhd)
    configurar_storage(VBoxManage, vmname, installer_vdi, runtime_vhd)
    iniciar_vm(VBoxManage, vmname)

    print("Instalação iniciada. Continue no VirtualBox.")


if __name__ == "__main__":
    main()
