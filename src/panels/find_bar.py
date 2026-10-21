"""Barra de localizar e substituir mostrada acima do editor.

A barra nao guarda estado de texto: a janela principal le os campos e chama
os metodos de busca/substituicao do `CodeEditor`. `mostrar`/`esconder`
alternam a visibilidade e devolvem o foco ao editor ao fechar. Enter no
campo de busca avanca para a proxima ocorrencia; Enter no campo de
substituicao troca a ocorrencia atual.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolButton,
    QWidget,
)


class FindBar(QWidget):

    fechar = Signal()
    procura_mudou = Signal(str, bool)  # texto, diferenciar maiusculas
    aviso = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.campo_busca = QLineEdit()
        self.campo_busca.setPlaceholderText("Localizar")
        self.campo_substituir = QLineEdit()
        self.campo_substituir.setPlaceholderText("Substituir por")

        self.botao_anterior = QToolButton()
        self.botao_anterior.setText("↑")
        self.botao_anterior.setToolTip("Ocorrencia anterior")
        self.botao_proxima = QToolButton()
        self.botao_proxima.setText("↓")
        self.botao_proxima.setToolTip("Proxima ocorrencia (Enter)")

        self.caixa_sensivel = QCheckBox("Aa")
        self.caixa_sensivel.setToolTip("Diferenciar maiusculas e minusculas")

        self.botao_substituir = QToolButton()
        self.botao_substituir.setText("Substituir")
        self.botao_substituir.setToolTip("Substitui a ocorrencia atual (Enter)")
        self.botao_tudo = QToolButton()
        self.botao_tudo.setText("Tudo")
        self.botao_tudo.setToolTip("Substitui todas as ocorrencias")

        self.botao_fechar = QToolButton()
        self.botao_fechar.setText("✕")
        self.botao_fechar.setToolTip("Fecha a busca (Esc)")

        self.rotulo = QLabel()
        self.rotulo.setMinimumWidth(110)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.addWidget(self.campo_busca)
        layout.addWidget(self.botao_anterior)
        layout.addWidget(self.botao_proxima)
        layout.addWidget(self.caixa_sensivel)
        layout.addWidget(self.rotulo)
        layout.addSpacing(12)
        layout.addWidget(self.campo_substituir)
        layout.addWidget(self.botao_substituir)
        layout.addWidget(self.botao_tudo)
        layout.addStretch(1)
        layout.addWidget(self.botao_fechar)

        self.botao_proxima.clicked.connect(self._proxima)
        self.botao_anterior.clicked.connect(self._anterior)
        self.botao_substituir.clicked.connect(self._substituir)
        self.botao_tudo.clicked.connect(self._substituir_tudo)
        self.botao_fechar.clicked.connect(self.fechar.emit)
        self.campo_busca.textChanged.connect(self._avisar_mudanca)
        self.campo_busca.returnPressed.connect(self._proxima)
        self.campo_substituir.returnPressed.connect(self._substituir)
        self.caixa_sensivel.toggled.connect(self._avisar_mudanca)

        self._modo_substituicao = False
        self._alternar_substituicao(False)

    # --- API da janela principal ---------------------------------------------

    def mostrar(self, com_substituicao: bool = False, texto: str = "") -> None:
        self._alternar_substituicao(com_substituicao)
        self.setVisible(True)
        if texto:
            self.campo_busca.setText(texto)
        self.campo_busca.selectAll()
        self.campo_busca.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def esconder(self) -> None:
        self.setVisible(False)
        self.mostrar_aviso("")
        self.procura_mudou.emit("", False)

    def texto_busca(self) -> str:
        return self.campo_busca.text()

    def texto_substituir(self) -> str:
        return self.campo_substituir.text()

    def diferenciar_maiusculas(self) -> bool:
        return self.caixa_sensivel.isChecked()

    def mostrar_aviso(self, texto: str) -> None:
        self.rotulo.setText(texto)

    # --- Internos ---------------------------------------------------------------

    def _alternar_substituicao(self, visivel: bool) -> None:
        self._modo_substituicao = visivel
        self.campo_substituir.setVisible(visivel)
        self.botao_substituir.setVisible(visivel)
        self.botao_tudo.setVisible(visivel)

    def _proxima(self) -> None:
        self.aviso.emit("proxima")

    def _anterior(self) -> None:
        self.aviso.emit("anterior")

    def _substituir(self) -> None:
        self.aviso.emit("substituir")

    def _substituir_tudo(self) -> None:
        self.aviso.emit("substituir_tudo")

    def _avisar_mudanca(self, *_args) -> None:
        self.aviso.emit("")
        self.procura_mudou.emit(self.campo_busca.text(), self.caixa_sensivel.isChecked())

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.fechar.emit()
            event.accept()
            return
        super().keyPressEvent(event)


__all__ = ["FindBar"]
