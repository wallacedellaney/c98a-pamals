"""Roda as 3 extrações (emergências, reparáveis, pagamentos) em sequência."""

import extrair_emergencias
import extrair_reparaveis
import extrair_pagamentos


def main():
    extrair_emergencias.main()
    extrair_reparaveis.main()
    extrair_pagamentos.main()


if __name__ == "__main__":
    main()
