"""Explorador de arquivos/pastas lateral, no estilo do VSCode.

Mostra a arvore de uma pasta raiz em um `QTreeWidget`: subpastas com carga
preguicosa (so montam os filhos quando abertas) e arquivos que, ao serem
duplamente clicados, emitem `arquivo_escolhido` para a janela principal
abrir no editor. Botoes no topo trocam a raiz (`pasta_escolhida`) e
recarregam a arvore.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QStyle,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

ROLE_CAMPO = Qt.ItemDataRole.UserRole
ROLE_EH_PASTA = Qt.ItemDataRole.UserRole + 1


def _ordenar(entradas: list[Path]) -> list[Path]:
    """Pastas primeiro, depois arquivos; ambos em ordem alfabetica."""
    return sorted(
        entradas,
        key=lambda item: (not item.is_dir(), item.name.lower()),
    )


class FileExplorer(QWidget):

    pasta_escolhida = Signal(str)
    arquivo_escolhido = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._raiz = ""

        self.titulo = QLabel("Arquivos")
        fonte = QFont()
        fonte.setBold(True)
        self.titulo.setFont(fonte)

        self.botao_pasta = QToolButton()
        self.botao_pasta.setText("Abrir pasta...")
        self.botao_pasta.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        )
        self.botao_pasta.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.botao_pasta.clicked.connect(self._escolher_pasta)

        self.botao_atualizar = QToolButton()
        self.botao_atualizar.setText("Atualizar")
        self.botao_atualizar.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        )
        self.botao_atualizar.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.botao_atualizar.clicked.connect(self.atualizar)

        self.arvore = QTreeWidget()
        self.arvore.setHeaderHidden(True)
        self.arvore.setColumnCount(1)
        self.arvore.itemExpanded.connect(self._expandir)
        self.arvore.itemDoubleClicked.connect(self._abrir_item)

        barra = QHBoxLayout()
        barra.setContentsMargins(0, 0, 0, 0)
        barra.addWidget(self.botao_pasta)
        barra.addWidget(self.botao_atualizar)
        barra.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.titulo)
        layout.addLayout(barra)
        layout.addWidget(self.arvore)

        self.arvore.header().setStretchLastSection(True)

    # --- Raiz e recarga ------------------------------------------------------

    def raiz(self) -> str:
        return self._raiz

    def definir_raiz(self, caminho: str) -> None:
        pasta = Path(caminho) if caminho else None
        if pasta is not None and not pasta.is_dir():
            pasta = None
        self._raiz = str(pasta) if pasta is not None else ""
        self.titulo.setText(f"Arquivos - {pasta.name}" if pasta else "Arquivos")
        self.atualizar()

    def atualizar(self) -> None:
        self.arvore.clear()
        if not self._raiz:
            return
        raiz = Path(self._raiz)
        entradas = _ordenar(
            [item for item in raiz.iterdir() if not item.name.startswith(".")]
        )
        for caminho in entradas:
            self.arvore.addTopLevelItem(self._criar_item(caminho))
        if self.arvore.topLevelItemCount() > 0:
            self.arvore.expandItem(self.arvore.topLevelItem(0))

    def marcar_arquivo_aberto(self, caminho: str) -> None:
        """Deixa o arquivo aberto em negrito na arvore (quando visivel)."""
        alvo = Path(caminho).resolve() if caminho else None
        for item in self._todos_os_itens():
            campo = item.data(0, ROLE_CAMPO) or ""
            fonte = item.font(0)
            destaque = alvo is not None and campo and Path(campo).resolve() == alvo
            fonte.setBold(bool(destaque))
            item.setFont(0, fonte)

    # --- Internos -------------------------------------------------------------

    def _criar_item(self, caminho: Path) -> QTreeWidgetItem:
        eh_pasta = caminho.is_dir()
        item = QTreeWidgetItem([caminho.name])
        item.setData(0, ROLE_CAMPO, str(caminho))
        item.setData(0, ROLE_EH_PASTA, eh_pasta)
        icone = self.style().standardIcon(
            QStyle.StandardPixmap.SP_DirIcon
            if eh_pasta
            else QStyle.StandardPixmap.SP_FileIcon
        )
        item.setIcon(0, icone)
        if eh_pasta:
            item.setChildIndicatorPolicy(
                QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicatorWhenChildless
            )
        return item

    def _carregar_filhos(self, item: QTreeWidgetItem) -> None:
        campo = item.data(0, ROLE_CAMPO) or ""
        if not campo:
            return
        item.takeChildren()
        pasta = Path(campo)
        try:
            entradas = _ordenar(
                [filho for filho in pasta.iterdir() if not filho.name.startswith(".")]
            )
        except OSError:
            return
        for caminho in entradas:
            item.addChild(self._criar_item(caminho))

    def _expandir(self, item: QTreeWidgetItem) -> None:
        if not item.data(0, ROLE_EH_PASTA):
            return
        if item.childCount() == 0:
            self._carregar_filhos(item)

    def _abrir_item(self, item: QTreeWidgetItem) -> None:
        campo = item.data(0, ROLE_CAMPO) or ""
        if not campo:
            return
        if item.data(0, ROLE_EH_PASTA):
            self.arvore.expandItem(item)
            return
        self.arquivo_escolhido.emit(campo)

    def _escolher_pasta(self) -> None:
        inicial = self._raiz or str(Path.home())
        caminho = QFileDialog.getExistingDirectory(self, "Abrir pasta", inicial)
        if caminho:
            self.pasta_escolhida.emit(caminho)

    def _todos_os_itens(self) -> list[QTreeWidgetItem]:
        encontrados: list[QTreeWidgetItem] = []

        def visitar(item: QTreeWidgetItem) -> None:
            encontrados.append(item)
            for indice in range(item.childCount()):
                visitar(item.child(indice))

        for indice in range(self.arvore.topLevelItemCount()):
            visitar(self.arvore.topLevelItem(indice))
        return encontrados


__all__ = ["FileExplorer"]
