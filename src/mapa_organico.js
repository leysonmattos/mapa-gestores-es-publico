/* Mapa de gestores no estilo dos mapas de apuração de eleição.
 *
 * Recebe o mapa Leaflet criado pelo folium e a configuração montada em
 * map_generator.py (municípios com a cor já resolvida, contorno do ES,
 * limites, gestores e legenda). Desenha:
 *   - os municípios sobre fundo escuro, com o contorno do estado em branco;
 *   - uma mira no centro da área livre: o município sob ela fica selecionado
 *     enquanto o mapa é arrastado, e clicar num município o leva até a mira;
 *   - um painel com os dados do município selecionado (folha inferior no
 *     celular, card no canto em telas largas);
 *   - nomes das cidades por ordem de população, sem sobreposição;
 *   - controles: "Como ler o mapa?", busca, tela cheia, zoom e voltar ao ES.
 */
function iniciarMapaOrganico(mapa, cfg) {
    'use strict';

    var area = mapa.getContainer();
    L.DomUtil.addClass(area, 'mapa-organico');

    // ---------- Utilidades ----------
    var ACENTOS = new RegExp('[' + String.fromCharCode(0x300) + '-' + String.fromCharCode(0x36f) + ']', 'g');
    var ENTIDADES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

    function semAcento(texto) {
        return String(texto || '').normalize('NFD').replace(ACENTOS, '').toLowerCase();
    }
    function escapar(texto) {
        return String(texto == null ? '' : texto).replace(/[&<>"']/g, function (c) { return ENTIDADES[c]; });
    }
    function inteiro(n) {
        return Number(n || 0).toLocaleString('pt-BR', { maximumFractionDigits: 0 });
    }
    function decimal(n, casas) {
        return Number(n || 0).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
    }
    function criar(tag, classe, pai, html) {
        var elemento = L.DomUtil.create(tag, classe || '', pai);
        if (html != null) { elemento.innerHTML = html; }
        return elemento;
    }
    function botao(classe, pai, html, rotulo) {
        var b = criar('button', classe, pai, html);
        b.type = 'button';
        if (rotulo) { b.setAttribute('aria-label', rotulo); b.title = rotulo; }
        return b;
    }
    // Cliques, toques e rolagem nos painéis não devem arrastar nem dar zoom no mapa.
    function isolar(elemento) {
        L.DomEvent.disableClickPropagation(elemento);
        L.DomEvent.disableScrollPropagation(elemento);
    }
    function iniciais(nome) {
        var partes = String(nome || '').trim().split(/\s+/);
        var primeira = (partes[0] || '').charAt(0);
        var ultima = partes.length > 1 ? partes[partes.length - 1].charAt(0) : '';
        return (primeira + ultima).toUpperCase();
    }

    // ---------- Ícones ----------
    var ICONE_INFO = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="9.5"/><path d="M12 11v6" stroke-linecap="round"/><circle cx="12" cy="7.6" r="1.2" fill="currentColor" stroke="none"/></svg>';
    var ICONE_LUPA = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5 21 21"/></svg>';
    var ICONE_VOLTAR = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/></svg>';
    var ICONE_PINO = '<svg width="14" height="18" viewBox="0 0 14 18" aria-hidden="true"><path d="M7 0C3.1 0 0 3.1 0 7c0 5.2 7 11 7 11s7-5.8 7-11c0-3.9-3.1-7-7-7z" fill="#e5322d"/><circle cx="7" cy="7" r="2.6" fill="#fff"/></svg>';
    // Bandeira do ES: faixas azul, branca e rosa, com o lema na faixa branca.
    var BANDEIRA_ES = '<svg class="mo-bandeira" viewBox="0 0 34 22" aria-hidden="true"><rect width="34" height="22" fill="#fff"/><rect width="34" height="7.4" fill="#3f6ab3"/><rect y="14.6" width="34" height="7.4" fill="#e6a2c6"/><rect x="8" y="10.3" width="18" height="1.4" rx="0.7" fill="#3f6ab3" opacity="0.75"/></svg>';

    // ---------- Municípios e contorno ----------
    var temMouse = !!(window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)').matches);
    var limites = L.latLngBounds(cfg.limites);
    var camadas = [];
    var selecionado = null;
    var sobMouse = null;
    var interagiu = false;
    var zInicial = mapa.getZoom();

    ['mo-contorno', 'mo-destaque', 'mo-rotulos'].forEach(function (nome, i) {
        var pane = mapa.createPane(nome);
        pane.style.zIndex = 450 + i * 5;
        pane.style.pointerEvents = 'none';
    });

    function estiloBase(props) {
        return { fillColor: props.cor, fillOpacity: 0.9, color: '#16181c', weight: 0.8, opacity: 0.6 };
    }

    // Os contornos brancos do município selecionado e do que está sob o
    // mouse vão numa camada à parte, sem eventos. Trazer o próprio polígono
    // para a frente (bringToFront) reinsere o elemento SVG no DOM, e o Chrome
    // perde o clique quando isso acontece entre o mousedown e o mouseup.
    var rendererDestaque = L.svg({ pane: 'mo-destaque', padding: 1 });
    var destaques = {};
    function destacar(tipo, camada, estiloLinha) {
        if (destaques[tipo]) { mapa.removeLayer(destaques[tipo]); destaques[tipo] = null; }
        if (camada) {
            destaques[tipo] = L.geoJSON(camada.feature.geometry, {
                pane: 'mo-destaque', renderer: rendererDestaque, interactive: false,
                style: L.extend({ fill: false, lineJoin: 'round' }, estiloLinha)
            }).addTo(mapa);
        }
    }
    function repintar(camada) {
        if (!camada) { return; }
        var s = estiloBase(camada.feature.properties);
        if (camada === selecionado) { s.fillOpacity = 1; }
        camada.setStyle(s);
    }

    L.geoJSON(cfg.municipios, {
        renderer: L.svg({ padding: 1 }),
        style: function (f) { return estiloBase(f.properties); },
        onEachFeature: function (f, camada) {
            var p = f.properties;
            camada._moLimites = camada.getBounds();
            camada._moRotulo = p.rotulo ? L.latLng(p.rotulo[0], p.rotulo[1]) : camada._moLimites.getCenter();
            camada._moNome = p.municipio || p.name || p.nome || '';
            camadas.push(camada);

            camada.on('click', function () {
                interagiu = true;
                centralizar(camada._moRotulo);
            });
            if (temMouse) {
                camada.bindTooltip(escapar(camada._moNome), {
                    sticky: true, direction: 'top', offset: [0, -10], className: 'mo-dica', opacity: 1
                });
                camada.on('mouseover', function () {
                    if (sobMouse === camada) { return; }
                    sobMouse = camada;
                    destacar('mouse', camada === selecionado ? null : camada,
                        { color: '#ffffff', weight: 1.4, opacity: 0.85 });
                });
                camada.on('mouseout', function () {
                    if (sobMouse !== camada) { return; }
                    sobMouse = null;
                    destacar('mouse', null);
                });
            }
        }
    }).addTo(mapa);

    if (cfg.contorno) {
        L.geoJSON(cfg.contorno, {
            pane: 'mo-contorno',
            interactive: false,
            renderer: L.svg({ pane: 'mo-contorno', padding: 1 }),
            style: { color: '#ffffff', weight: 2.4, opacity: 0.95, fill: false, lineJoin: 'round' }
        }).addTo(mapa);
    }

    // ---------- Interface ----------
    var ui = criar('div', 'mo-ui', area);
    criar('div', 'mo-mira-h', ui);
    criar('div', 'mo-mira-v', ui);
    criar('div', 'mo-mira-alvo', ui);
    var etiqueta = criar('div', 'mo-etiqueta mo-oculta', ui);
    etiqueta.setAttribute('aria-live', 'polite');

    var topoEsq = criar('div', 'mo-topo-esq', ui);
    var botaoAjuda = botao('mo-botao mo-ajuda', topoEsq,
        '<span class="mo-icone-i">' + ICONE_INFO + '</span>Como ler o mapa?');

    var topoDir = criar('div', 'mo-topo-dir', ui);
    var botaoBusca = botao('mo-botao', topoDir, ICONE_LUPA, 'Buscar município');
    botaoBusca.setAttribute('aria-expanded', 'false');
    var busca = criar('div', 'mo-busca', topoDir);
    busca.hidden = true;
    var campo = criar('input', '', busca);
    campo.type = 'search';
    campo.placeholder = 'Buscar município';
    campo.autocomplete = 'off';
    campo.setAttribute('aria-label', 'Buscar município');
    var lista = criar('ul', 'mo-resultados', busca);

    var pilha = criar('div', 'mo-pilha', ui);
    var zoom = criar('div', 'mo-zoom', pilha);
    var botaoMais = botao('mo-botao', zoom, '+', 'Aproximar');
    var botaoMenos = botao('mo-botao', zoom, '−', 'Afastar');
    // O botão de tela cheia do plugin vem para a pilha; continua sendo o
    // mesmo elemento, então os ouvintes do plugin e de TelaCheiaEmIframe valem.
    var botaoTela = area.querySelector('.leaflet-control-zoom-fullscreen');
    if (botaoTela && botaoTela.parentNode) {
        pilha.insertBefore(botaoTela.parentNode, zoom);
    }

    var botaoVoltar = botao('mo-voltar', ui, ICONE_VOLTAR + BANDEIRA_ES + '<span>ES</span>', 'Ver o estado inteiro');

    var painel = criar('div', 'mo-painel', ui);
    painel.setAttribute('role', 'region');
    painel.setAttribute('aria-label', 'Detalhes do município');
    var alca = botao('mo-alca', painel, '', 'Recolher painel');
    alca.setAttribute('aria-expanded', 'true');
    var cabecalho = criar('div', 'mo-cabecalho', painel);
    var abas = criar('div', 'mo-abas', painel);
    abas.setAttribute('role', 'tablist');
    var conteudo = criar('div', 'mo-conteudo', painel);

    var ABAS = [['gestor', 'Gestor'], ['municipio', 'Município']];
    if (!cfg.modoPublico) { ABAS.push(['atuacao', 'Atuação']); }
    var abaAtual = 'gestor';
    var botoesAba = ABAS.map(function (a) {
        var b = botao('mo-aba', abas, a[1]);
        b.setAttribute('role', 'tab');
        b.setAttribute('data-aba', a[0]);
        L.DomEvent.on(b, 'click', function () {
            abaAtual = a[0];
            renderizarPainel();
        });
        return b;
    });

    var fundoModal = criar('div', 'mo-modal-fundo', ui, htmlModal());
    fundoModal.hidden = true;

    [topoEsq, topoDir, pilha, botaoVoltar, painel, fundoModal].forEach(isolar);

    // ---------- Layout: área livre e posição da mira ----------
    // A mira fica no centro da parte do mapa que o painel não cobre. A altura
    // do painel no celular é fixa (CSS), para que trocar de município ou de aba
    // não mova a mira — o que mudaria a seleção sem o usuário mexer no mapa.
    var ALTURA_RECOLHIDO = 64;
    var mira = L.point(0, 0);
    var livre = { x0: 0, y0: 0, x1: 0, y1: 0 };
    var recolhido = false;

    function medirLayout() {
        var W = area.clientWidth;
        var H = area.clientHeight;
        // 600 px: a coluna do mapa no Streamlit em desktop tem ~670 px e já
        // usa o card; celulares (360-430 px) ficam com a folha inferior.
        var largo = W >= 600;
        if (largo) { L.DomUtil.addClass(area, 'mo-largo'); } else { L.DomUtil.removeClass(area, 'mo-largo'); }

        var baseEsq, baseDir;
        if (largo) {
            var direitaPainel = 14 + painel.offsetWidth;
            var topoPainel = H - 14 - painel.offsetHeight;
            livre = { x0: direitaPainel, y0: 0, x1: W, y1: H };
            baseEsq = H - topoPainel + 12;
            baseDir = 16;
        } else {
            var visivel = recolhido ? ALTURA_RECOLHIDO : painel.offsetHeight;
            livre = { x0: 0, y0: 0, x1: W, y1: H - visivel };
            baseEsq = visivel + 12;
            baseDir = visivel + 12;
        }
        mira = L.point(Math.round((livre.x0 + livre.x1) / 2), Math.round((livre.y0 + livre.y1) / 2));
        ui.style.setProperty('--mo-mira-x', mira.x + 'px');
        ui.style.setProperty('--mo-mira-y', mira.y + 'px');
        ui.style.setProperty('--mo-base-esq', baseEsq + 'px');
        ui.style.setProperty('--mo-base-dir', baseDir + 'px');
    }

    // Leva um ponto até a mira (não até o centro do contêiner).
    function centralizar(latlng, zoomAlvo) {
        var z = zoomAlvo == null ? mapa.getZoom() : zoomAlvo;
        var desloc = mira.subtract(mapa.getSize().divideBy(2));
        var alvo = mapa.unproject(mapa.project(latlng, z).subtract(desloc), z);
        mapa.flyTo(alvo, z, { duration: 0.6, easeLinearity: 0.3 });
    }

    // Enquadra o estado inteiro na área livre, abaixo dos botões do topo e,
    // no celular, acima do botão "ES" (que fica sobre o mapa, no canto).
    function enquadrar(animar) {
        var W = area.clientWidth;
        var H = area.clientHeight;
        var folgaBaixo = L.DomUtil.hasClass(area, 'mo-largo') ? 20 : botaoVoltar.offsetHeight + 24;
        var opcoes = {
            paddingTopLeft: L.point(livre.x0 + 20, Math.max(livre.y0, 60) + 8),
            paddingBottomRight: L.point(W - livre.x1 + 20, H - livre.y1 + folgaBaixo)
        };
        if (animar) {
            mapa.flyToBounds(limites, L.extend({ duration: 0.7 }, opcoes));
        } else {
            mapa.fitBounds(limites, L.extend({ animate: false }, opcoes));
        }
    }

    // Zoom mínimo um pouco abaixo do enquadramento do estado; libera antes de
    // enquadrar, senão um contêiner menor (ao sair da tela cheia) seria
    // impedido de afastar o suficiente.
    // O limite de navegação é o estado com uma folga do próprio tamanho em
    // cada lado — o bastante para levar qualquer município à mira, sem deixar
    // um arraste com inércia perder o estado de vista — e nunca menor que a
    // vista do enquadramento: em tela larga a mira fica à direita do centro
    // (o card ocupa a esquerda) e um limite justo empurraria o estado de volta.
    function enquadrarInicial() {
        mapa.setMaxBounds(null);
        mapa.setMinZoom(0);
        enquadrar(false);
        zInicial = mapa.getZoom();
        mapa.setMinZoom(Math.max(zInicial - 0.75, 4));
        mapa.setMaxBounds(limites.pad(1).extend(mapa.getBounds()));
    }

    // ---------- Seleção pela mira ----------
    function dentroAnel(x, y, anel) {
        var dentro = false;
        for (var i = 0, j = anel.length - 1; i < anel.length; j = i++) {
            var xi = anel[i][0], yi = anel[i][1], xj = anel[j][0], yj = anel[j][1];
            if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) {
                dentro = !dentro;
            }
        }
        return dentro;
    }
    function dentroPoligono(x, y, aneis) {
        if (!dentroAnel(x, y, aneis[0])) { return false; }
        for (var k = 1; k < aneis.length; k++) {
            if (dentroAnel(x, y, aneis[k])) { return false; }
        }
        return true;
    }
    function contem(geometria, x, y) {
        if (geometria.type === 'Polygon') { return dentroPoligono(x, y, geometria.coordinates); }
        if (geometria.type === 'MultiPolygon') {
            return geometria.coordinates.some(function (p) { return dentroPoligono(x, y, p); });
        }
        return false;
    }
    function municipioEm(latlng) {
        for (var i = 0; i < camadas.length; i++) {
            var c = camadas[i];
            if (c._moLimites.contains(latlng) && contem(c.feature.geometry, latlng.lng, latlng.lat)) {
                return c;
            }
        }
        return null;
    }

    function atualizarSelecao() {
        var achado = municipioEm(mapa.containerPointToLatLng(mira));
        if (achado === selecionado) { return; }
        var anterior = selecionado;
        selecionado = achado;
        repintar(anterior);
        repintar(achado);
        destacar('selecao', achado, { color: '#ffffff', weight: 2.6, opacity: 1 });
        if (achado && achado === sobMouse) { destacar('mouse', null); }
        renderizarEtiqueta();
        renderizarPainel();
    }

    var selecaoAgendada = false;
    function agendarSelecao() {
        if (selecaoAgendada) { return; }
        selecaoAgendada = true;
        L.Util.requestAnimFrame(function () {
            selecaoAgendada = false;
            atualizarSelecao();
        });
    }

    // ---------- Etiqueta e painel ----------
    function renderizarEtiqueta() {
        if (!selecionado) {
            L.DomUtil.addClass(etiqueta, 'mo-oculta');
            return;
        }
        etiqueta.innerHTML = ICONE_PINO + '<span class="mo-uf-etiqueta">ES</span><span class="mo-sep">•</span>' +
            '<strong>' + escapar(selecionado._moNome) + '</strong>';
        L.DomUtil.removeClass(etiqueta, 'mo-oculta');
    }

    function gestorDe(props) {
        var chave = String(props.gestor || '').toUpperCase();
        var info = cfg.gestores[chave];
        return info ? { chave: chave, info: info } : null;
    }

    function numero(rotulo, valor, unidade) {
        return '<div><div class="mo-rotulo-num">' + rotulo + '</div><div class="mo-valor">' + valor +
            '</div><div class="mo-unidade">' + unidade + '</div></div>';
    }

    function htmlGestor(gestor) {
        if (!gestor) {
            return '<div class="mo-dica-texto">Gestor não informado para este município.</div>';
        }
        var g = gestor.info;
        var whatsapp = g.wa_link
            ? '<a class="mo-link" href="' + escapar(g.wa_link) + '" target="_blank" rel="noopener">Chamar no WhatsApp ›</a>'
            : '';
        return '<div class="mo-gestor">' +
                '<div class="mo-avatar" style="background:' + g.cor + ';border-color:' + g.borda + '">' + escapar(iniciais(g.nome)) + '</div>' +
                '<div><div class="mo-gestor-nome">' + escapar(g.nome) + '</div>' +
                '<div class="mo-gestor-fone">' + escapar(g.fone) + '</div></div>' +
            '</div>' +
            '<div class="mo-faixa" style="background:' + g.cor + ';color:#14171c">' + escapar(gestor.chave) + '</div>' +
            '<div class="mo-rodape-gestor"><span class="mo-gestor-regiao">' + escapar(g.regiao) + '</span>' + whatsapp + '</div>';
    }

    function htmlMunicipio(p) {
        return '<div class="mo-numeros">' +
                numero('População', inteiro(p.populacao), 'habitantes') +
                numero('Área', decimal(p.area_km2, 1), 'km²') +
                numero('Densidade', decimal(p.densidade, 1), 'hab/km²') +
            '</div>' +
            '<div class="mo-rodape">' + escapar(p.microrregiao) + ' · ' + escapar(p.mesorregiao) +
            '<br>Código IBGE <strong>' + escapar(p.cod_ibge || p.codarea) + '</strong></div>';
    }

    function htmlAtuacao(p) {
        function coluna(rotulo, valor, ranking, perc, cor, sigla) {
            return '<div><div class="mo-rotulo-num">' + rotulo + '</div>' +
                '<div class="mo-valor">' + inteiro(valor) + '</div>' +
                '<div class="mo-unidade">' + ranking + 'º no ES · ' + decimal(perc, 1) + '% do ES</div>' +
                '<div class="mo-faixa" style="background:' + cor + ';color:#ffffff">' + sigla + '</div></div>';
        }
        return '<div class="mo-numeros mo-dois">' +
                coluna('PJ Academias', p.pj_academias, p.ranking_pj, p.perc_pj, '#2563eb', 'PJ') +
                coluna('Profissionais PF', p.pf_profissionais, p.ranking_pf, p.perc_pf, '#059669', 'PF') +
            '</div>' +
            '<div class="mo-rodape">Total de atuação (PF + PJ): <strong>' + inteiro(p.total) + '</strong></div>';
    }

    function htmlResumoEstado() {
        var linhas = cfg.legenda.map(function (g) {
            var selos = cfg.modoPublico ? '' :
                '<span class="mo-selo mo-selo-pj">' + inteiro(g.pj) + ' PJ</span>' +
                '<span class="mo-selo mo-selo-pf">' + inteiro(g.pf) + ' PF</span>';
            return '<div class="mo-linha-gestor"><span class="mo-quadrado" style="background:' + g.cor + '"></span>' +
                '<span class="mo-g-nome">' + escapar(g.chave) + ' <span>· ' + g.municipios + ' municípios</span></span>' +
                selos + '</div>';
        }).join('');
        return '<div class="mo-dica-texto">Arraste o mapa até um município ou toque nele.</div>' + linhas;
    }

    function renderizarPainel() {
        var p = selecionado ? selecionado.feature.properties : null;
        if (!p) {
            cabecalho.innerHTML = '<span class="mo-uf">ES</span><span class="mo-nome">Espírito Santo</span>';
            abas.hidden = true;
            conteudo.innerHTML = htmlResumoEstado();
        } else {
            var gestor = gestorDe(p);
            cabecalho.innerHTML = '<span class="mo-uf">ES</span><span class="mo-nome">' + escapar(selecionado._moNome) + '</span>' +
                (gestor ? '<span class="mo-tag" style="background:' + gestor.info.cor + '">' + escapar(gestor.chave) + '</span>' : '');
            abas.hidden = false;
            botoesAba.forEach(function (b) {
                var ativa = b.getAttribute('data-aba') === abaAtual;
                if (ativa) { L.DomUtil.addClass(b, 'mo-ativa'); } else { L.DomUtil.removeClass(b, 'mo-ativa'); }
                b.setAttribute('aria-selected', ativa ? 'true' : 'false');
            });
            conteudo.innerHTML = abaAtual === 'municipio' ? htmlMunicipio(p)
                : abaAtual === 'atuacao' ? htmlAtuacao(p)
                : htmlGestor(gestor);
        }
        // No card de tela larga a altura acompanha o conteúdo; o botão
        // "voltar" fica logo acima dele.
        if (L.DomUtil.hasClass(area, 'mo-largo')) { medirLayout(); }
    }

    // ---------- Janela "Como ler o mapa?" ----------
    function htmlModal() {
        var linhas = cfg.legenda.map(function (g) {
            return '<div class="mo-legenda-linha"><span class="mo-quadrado" style="background:' + g.cor + '"></span>' +
                '<strong>' + escapar(g.nome) + '</strong><span>' + g.municipios + ' municípios</span></div>';
        }).join('');
        var escala = '';
        if (cfg.escala) {
            escala = '<div class="mo-escala">Municípios de gestores desmarcados, cor por: ' + escapar(cfg.escala.titulo) +
                '<div class="mo-escala-barra" style="background:linear-gradient(to right,' + cfg.escala.cores.join(',') + ')"></div>' +
                '<div class="mo-escala-limites"><span>' + inteiro(cfg.escala.min) + '</span><span>' + inteiro(cfg.escala.max) + '</span></div></div>';
        }
        return '<div class="mo-modal" role="dialog" aria-modal="true" aria-labelledby="mo-titulo-modal">' +
            '<h3 id="mo-titulo-modal">Gestores por região</h3>' +
            '<p>O mapa mostra a cor do gestor responsável por cada município. Arraste o mapa: o município que fica sob a mira aparece no painel. Toque num município para levá-lo até a mira.</p>' +
            '<div class="mo-legenda">' + linhas + '</div>' + escala +
            '<div class="mo-nota">* Malha municipal e dados demográficos: IBGE</div>' +
            '<button type="button" class="mo-ok">OK</button></div>';
    }

    var botaoOk = fundoModal.querySelector('.mo-ok');
    function abrirAjuda() {
        fundoModal.hidden = false;
        botaoOk.focus();
    }
    function fecharAjuda() {
        if (fundoModal.hidden) { return; }
        fundoModal.hidden = true;
        botaoAjuda.focus();
    }
    L.DomEvent.on(botaoAjuda, 'click', abrirAjuda);
    L.DomEvent.on(botaoOk, 'click', fecharAjuda);
    L.DomEvent.on(fundoModal, 'click', function (e) {
        if (e.target === fundoModal) { fecharAjuda(); }
    });
    L.DomEvent.on(document, 'keydown', function (e) {
        if (e.key === 'Escape') { fecharAjuda(); }
    });

    // ---------- Busca ----------
    var indice = camadas.map(function (c) {
        return { camada: c, chave: semAcento(c._moNome) };
    }).sort(function (a, b) { return a.camada._moNome.localeCompare(b.camada._moNome, 'pt-BR'); });
    var primeiroResultado = null;

    function abrirBusca(abrir) {
        busca.hidden = !abrir;
        botaoBusca.setAttribute('aria-expanded', abrir ? 'true' : 'false');
        if (abrir) {
            campo.value = '';
            filtrar();
            campo.focus();
        }
    }
    function irPara(camada) {
        abrirBusca(false);
        interagiu = true;
        centralizar(camada._moRotulo, Math.min(mapa.getMaxZoom(), Math.max(mapa.getZoom(), zInicial + 1.25)));
    }
    function filtrar() {
        var termo = semAcento(campo.value).trim();
        var achados = termo ? indice.filter(function (i) { return i.chave.indexOf(termo) !== -1; }) : [];
        // Quem começa com o termo vem primeiro: "barra" lista Barra de São
        // Francisco antes de Conceição da Barra.
        achados.sort(function (a, b) { return (b.chave.indexOf(termo) === 0) - (a.chave.indexOf(termo) === 0); });
        lista.innerHTML = '';
        primeiroResultado = achados.length ? achados[0].camada : null;
        if (termo && !achados.length) {
            criar('li', 'mo-sem-resultado', lista, 'Nenhum município encontrado');
            return;
        }
        achados.slice(0, 8).forEach(function (i, n) {
            var item = criar('li', '', lista);
            var b = botao('mo-resultado' + (n === 0 ? ' mo-ativo' : ''), item,
                '<span class="mo-quadrado" style="background:' + i.camada.feature.properties.cor + '"></span>' + escapar(i.camada._moNome));
            L.DomEvent.on(b, 'click', function () { irPara(i.camada); });
        });
    }
    L.DomEvent.on(botaoBusca, 'click', function () { abrirBusca(busca.hidden); });
    L.DomEvent.on(campo, 'input', filtrar);
    // Teclas digitadas na busca não podem chegar ao teclado do Leaflet
    // ("+" e "-" dariam zoom, setas moveriam o mapa).
    L.DomEvent.on(campo, 'keydown', function (e) {
        L.DomEvent.stopPropagation(e);
        if (e.key === 'Enter' && primeiroResultado) { irPara(primeiroResultado); }
        if (e.key === 'Escape') { abrirBusca(false); botaoBusca.focus(); }
    });
    L.DomEvent.on(campo, 'keyup keypress', L.DomEvent.stopPropagation);

    // ---------- Zoom, voltar e painel recolhível ----------
    // O zoom dos botões gira em torno da mira, para o município selecionado
    // não escapar dela.
    function zoomNaMira(delta) {
        interagiu = true;
        var z = Math.min(mapa.getMaxZoom(), Math.max(mapa.getMinZoom(), mapa.getZoom() + delta));
        mapa.setZoomAround(mira, z);
    }
    L.DomEvent.on(botaoMais, 'click', function () { zoomNaMira(0.75); });
    L.DomEvent.on(botaoMenos, 'click', function () { zoomNaMira(-0.75); });

    L.DomEvent.on(botaoVoltar, 'click', function () {
        interagiu = false;
        enquadrar(true);
    });

    // Recolher o painel move a mira para baixo; o mapa acompanha o mesmo
    // tanto, para o município selecionado continuar sob ela.
    function alternarPainel() {
        var antes = mira.y;
        recolhido = !recolhido;
        if (recolhido) { L.DomUtil.addClass(painel, 'mo-recolhido'); } else { L.DomUtil.removeClass(painel, 'mo-recolhido'); }
        alca.setAttribute('aria-expanded', recolhido ? 'false' : 'true');
        alca.setAttribute('aria-label', recolhido ? 'Expandir painel' : 'Recolher painel');
        alca.title = alca.getAttribute('aria-label');
        medirLayout();
        mapa.panBy([0, antes - mira.y], { duration: 0.25 });
    }
    L.DomEvent.on(alca, 'click', alternarPainel);
    L.DomEvent.on(cabecalho, 'click', function () {
        if (recolhido) { alternarPainel(); }
    });

    // ---------- Rótulos das cidades ----------
    // Por ordem de peso (capital primeiro, depois população); um nome só
    // aparece se não encostar num já mostrado, e o limiar de população cai
    // conforme o zoom aumenta.
    var rotulos = camadas.map(function (c) {
        var p = c.feature.properties;
        var marcador = L.marker(c._moRotulo, {
            pane: 'mo-rotulos',
            interactive: false,
            keyboard: false,
            icon: L.divIcon({
                className: 'mo-rotulo',
                iconSize: null,
                html: '<div class="mo-rotulo-conteudo"><span class="mo-ponto"></span><span>' + escapar(c._moNome) + '</span></div>'
            })
        }).addTo(mapa);
        var capital = String(p.codarea || p.cod_ibge) === String(cfg.capital);
        return { marcador: marcador, peso: capital ? Infinity : Number(p.populacao || 0) };
    }).sort(function (a, b) { return b.peso - a.peso; });

    function atualizarRotulos() {
        var d = mapa.getZoom() - zInicial;
        var limiar = d < 0.5 ? 150000 : d < 1.25 ? 50000 : d < 2 ? 15000 : 0;
        var ocupadas = [];
        rotulos.forEach(function (r) {
            var elemento = r.marcador.getElement();
            if (!elemento) { return; }
            var mostrar = r.peso >= limiar;
            if (mostrar) {
                var b = elemento.firstChild.getBoundingClientRect();
                var caixa = { l: b.left - 6, t: b.top - 4, r: b.right + 6, b: b.bottom + 4 };
                mostrar = !ocupadas.some(function (o) {
                    return caixa.l < o.r && caixa.r > o.l && caixa.t < o.b && caixa.b > o.t;
                });
                if (mostrar) { ocupadas.push(caixa); }
            }
            elemento.style.visibility = mostrar ? '' : 'hidden';
        });
    }

    // ---------- Eventos do mapa ----------
    mapa.on('dragstart', function () { interagiu = true; });
    L.DomEvent.on(area, 'wheel', function () { interagiu = true; });
    mapa.on('move zoomend moveend', agendarSelecao);
    mapa.on('zoomend', atualizarRotulos);
    // O st_folium dimensiona o iframe depois que o mapa nasce, e a tela cheia
    // muda o tamanho do contêiner: refaz o layout e, se o usuário ainda não
    // mexeu no mapa, o enquadramento do estado.
    mapa.on('resize', function () {
        medirLayout();
        if (!interagiu) { enquadrarInicial(); }
        atualizarRotulos();
        agendarSelecao();
    });

    // ---------- Início ----------
    renderizarPainel();
    medirLayout();
    enquadrarInicial();
    atualizarRotulos();
    atualizarSelecao();
    if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(atualizarRotulos);
    }
}
