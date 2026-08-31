from ops_common.http.pagination import Pagina, ParametrosPagina


def test_offset_e_limit():
    params = ParametrosPagina(pagina=3, tamanho=25)
    assert params.offset == 50
    assert params.limit == 25


def test_total_de_paginas_arredonda_para_cima():
    pagina = Pagina.de(itens=[1, 2, 3], total=51, params=ParametrosPagina(pagina=1, tamanho=25))
    assert pagina.total_paginas == 3
    assert pagina.tamanho == 25
