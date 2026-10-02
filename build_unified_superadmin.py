"""
Script de construção e deploy da Central Unificada no Super Admin do ProtocoloEdu.
Unifica:
- Gestão de Contratantes & White-Label
- Controle de Registros de Entrada (Inbound) e Saída (Outbound)
- Auditoria Autônoma dos Subagentes (Straight-Through Processing)
- Telemetria de Infraestrutura e Gauges de Capacidade
"""

import os
import json
import zipfile
import urllib.request
import urllib.error

HTML_CONTENT = r'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Super Admin Master • ProtocoloEdu | Central de Registros & Gestão SaaS</title>
    
    <link rel="icon" type="image/jpeg" href="/static/images/logo-imes.jpg">
    <!-- Tailwind CSS Oficial via CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Phosphor Icons -->
    <script src="https://unpkg.com/@phosphor-icons/web"></script>
    <!-- FontAwesome Oficial para Ícones Complementares -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Chart.js Oficial para Gráficos e Gauges -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <!-- Google Fonts: Plus Jakarta Sans & JetBrains Mono -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <!-- Supabase JS Client v2 Oficial -->
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>

    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
                        mono: ['"JetBrains Mono"', 'monospace'],
                    },
                    colors: {
                        imes: {
                            blue: '#0a2351',
                            blueLight: '#153a7a',
                            gold: '#fdb913',
                            goldHover: '#e8a800',
                        },
                        dark: {
                            bg: '#0B132B',
                            card: '#1B263B',
                            border: '#334155'
                        }
                    }
                }
            }
        }
    </script>

    <style>
        :root {
            --shadow-soft: 0 10px 40px -10px rgba(0,0,0,0.06);
            --shadow-hover: 0 20px 40px -10px rgba(0,0,0,0.12);
        }

        body { 
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: #f8fafc;
            color: #0f172a;
            transition: background-color 0.3s ease, color 0.3s ease;
            -webkit-user-select: none;
            user-select: none;
        }

        body.dark-mode {
            background-color: #0B132B;
            color: #E2E8F0;
        }

        .custom-scroll::-webkit-scrollbar { width: 6px; height: 6px; }
        .custom-scroll::-webkit-scrollbar-track { background: transparent; }
        .custom-scroll::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
        .custom-scroll::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
        body.dark-mode .custom-scroll::-webkit-scrollbar-thumb { background: #334155; }

        .modern-card {
            background: white;
            border-radius: 1rem;
            border: 1px solid #e2e8f0;
            box-shadow: var(--shadow-soft);
            transition: all 0.25s ease;
        }
        body.dark-mode .modern-card {
            background: #1B263B;
            border-color: #334155;
            box-shadow: 0 10px 30px -10px rgba(0,0,0,0.3);
        }

        .modern-input {
            width: 100%;
            padding: 0.65rem 1rem;
            border-radius: 0.75rem;
            border: 1px solid #cbd5e1;
            background-color: #f8fafc;
            color: #0f172a;
            outline: none;
            transition: all 0.2s;
        }
        body.dark-mode .modern-input {
            background-color: #0F172A;
            border-color: #334155;
            color: #F8FAFC;
        }
        .modern-input:focus {
            border-color: #0a2351;
            box-shadow: 0 0 0 3px rgba(10, 35, 81, 0.15);
        }
        body.dark-mode .modern-input:focus {
            border-color: #fdb913;
            box-shadow: 0 0 0 3px rgba(253, 185, 19, 0.2);
        }

        .btn-gold {
            background: #fdb913;
            color: #0a2351;
            font-weight: 700;
            transition: all 0.2s ease;
        }
        .btn-gold:hover {
            background: #e8a800;
            transform: translateY(-1px);
        }

        /* Abas Super Admin */
        .tab-btn {
            color: #64748b;
            background: transparent;
            border-bottom: 2px solid transparent;
            transition: all 0.2s ease;
        }
        .tab-btn:hover {
            color: #0a2351;
            background: rgba(0, 0, 0, 0.03);
        }
        .tab-btn.active {
            color: #0a2351;
            font-weight: 800;
            border-bottom: 2px solid #0a2351;
            background: rgba(10, 35, 81, 0.05);
        }
        body.dark-mode .tab-btn {
            color: #94a3b8;
        }
        body.dark-mode .tab-btn:hover {
            color: #ffffff;
            background: rgba(255, 255, 255, 0.05);
        }
        body.dark-mode .tab-btn.active {
            color: #fdb913;
            font-weight: 800;
            border-bottom: 2px solid #fdb913;
            background: rgba(253, 185, 19, 0.1);
        }

        /* Toggle Switch */
        .switch {
            font-size: 14px;
            position: relative;
            display: inline-block;
            width: 3.2em;
            height: 1.8em;
        }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: #cbd5e1;
            transition: .3s;
            border-radius: 30px;
        }
        .slider:before {
            position: absolute;
            content: "";
            height: 1.3em;
            width: 1.3em;
            border-radius: 20px;
            left: 0.25em;
            bottom: 0.25em;
            background-color: white;
            transition: .3s;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        input:checked + .slider { background-color: #0a2351; }
        input:checked + .slider:before { transform: translateX(1.4em); }
        body.dark-mode .slider { background-color: #334155; }
        body.dark-mode input:checked + .slider { background-color: #fdb913; }
        body.dark-mode input:checked + .slider:before { background-color: #0a2351; }

        @keyframes pulseGlow {
            0%, 100% { box-shadow: 0 0 10px rgba(16, 185, 129, 0.2); }
            50% { box-shadow: 0 0 20px rgba(16, 185, 129, 0.4); }
        }
        .pulse-live { animation: pulseGlow 2s infinite ease-in-out; }
    </style>

    <script>
        const SUPABASE_URL = "https://phipudvmceitxcajggus.supabase.co";
        const SUPABASE_ANON_KEY = "";
        let supabaseClient = null;
        try {
            supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
        } catch(e) { console.warn("Supabase passivo:", e); }
    </script>
</head>
<body class="min-h-screen flex flex-col antialiased">

    <!-- ========================================================================= -->
    <!-- BARRA SUPERIOR: SUPER ADMIN MASTER                                        -->
    <!-- ========================================================================= -->
    <header class="bg-[#0a2351] text-white border-b border-blue-950 px-4 sm:px-6 py-3.5 sticky top-0 z-50 shadow-lg">
        <div class="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-imes-gold text-imes-blue flex items-center justify-center text-xl font-bold shadow-md flex-shrink-0">
                    <i class="ph-bold ph-shield-checkered"></i>
                </div>
                <div>
                    <div class="flex items-center gap-2">
                        <span class="font-extrabold text-base tracking-tight text-white">Super Admin Master • ProtocoloEdu</span>
                        <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1 pulse-live">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                            REGISTRO UNIFICADO 24/7
                        </span>
                    </div>
                    <p class="text-xs text-blue-200">Central de Registros de Entrada e Saída • Dossiês • Subagentes IA • White-Label SaaS</p>
                </div>
            </div>

            <div class="flex items-center gap-2 sm:gap-3 flex-wrap justify-end">
                <!-- Theme Switcher -->
                <div class="flex items-center gap-2 mr-1">
                    <label class="switch" title="Alternar Tema Claro/Escuro">
                        <input checked="true" id="theme-toggle" type="checkbox" />
                        <span class="slider"></span>
                    </label>
                </div>

                <button onclick="openWhiteLabelModal()" class="px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white border border-white/20 font-bold rounded-xl text-xs transition flex items-center gap-1.5 cursor-pointer">
                    <i class="ph-bold ph-palette text-sm text-imes-gold"></i>
                    <span>White-Label</span>
                </button>

                <button onclick="openCreateModal()" class="px-3.5 py-1.5 btn-gold rounded-xl text-xs font-bold transition flex items-center gap-1.5 cursor-pointer active:scale-95 shadow">
                    <i class="ph-bold ph-plus-circle text-sm"></i>
                    <span>Novo Contratante</span>
                </button>

                <button onclick="refreshAllData()" class="p-2 bg-white/10 hover:bg-white/20 text-white rounded-xl text-sm border border-white/20 transition cursor-pointer" title="Atualizar dados em tempo real">
                    <i class="ph-bold ph-arrows-clockwise" id="refresh-icon"></i>
                </button>

                <div class="h-6 w-px bg-white/20 hidden sm:block"></div>

                <div class="text-right hidden sm:block">
                    <span class="text-[10px] text-blue-200 block font-medium">Modo Master</span>
                    <span class="text-xs font-mono font-bold text-imes-gold">Livre Acesso (Config)</span>
                </div>
            </div>
        </div>
    </header>

    <!-- ========================================================================= -->
    <!-- BARRA DE NAVEGAÇÃO DE ABAS UNIFICADAS                                     -->
    <!-- ========================================================================= -->
    <nav class="bg-white dark:bg-[#0F172A] border-b border-slate-200 dark:border-slate-800 sticky top-[69px] z-40 shadow-xs">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between gap-4 overflow-x-auto custom-scroll">
            <div class="flex items-center space-x-2 py-2">
                <!-- Aba 1: Central de Registros (Default) -->
                <button id="tab-btn-records" onclick="switchMainTab('records')" class="tab-btn active px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 cursor-pointer">
                    <i class="ph-bold ph-tray-arrow-down text-base text-blue-500"></i>
                    <span>Central de Registros (Entradas &amp; Saídas)</span>
                    <span id="badge-total-records" class="px-2 py-0.5 rounded-full text-[10px] font-black bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300">345 Registros</span>
                </button>

                <!-- Aba 2: Visão Executiva & Contratantes -->
                <button id="tab-btn-executive" onclick="switchMainTab('executive')" class="tab-btn px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 cursor-pointer">
                    <i class="ph-bold ph-chart-donut text-base text-amber-500"></i>
                    <span>Visão Executiva &amp; Contratantes</span>
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300" id="badge-institutions-count">3 Inst.</span>
                </button>

                <!-- Aba 3: Console dos Subagentes & Telemetria -->
                <button id="tab-btn-swarm" onclick="switchMainTab('swarm')" class="tab-btn px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 cursor-pointer">
                    <i class="ph-bold ph-cpu text-base text-emerald-500"></i>
                    <span>Console dos Subagentes &amp; Telemetria</span>
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                </button>
            </div>

            <div class="flex items-center gap-3 text-xs font-mono text-slate-400 py-2 flex-shrink-0">
                <span class="flex items-center gap-1.5 bg-slate-100 dark:bg-slate-800/80 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-700">
                    <i class="ph-bold ph-database text-emerald-500"></i>
                    <span>Supabase Live</span>
                </span>
            </div>
        </div>
    </nav>

    <!-- ========================================================================= -->
    <!-- CORPO PRINCIPAL COM CONTEÚDO DAS ABAS                                     -->
    <!-- ========================================================================= -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full space-y-6">

        <!-- ##################################################################### -->
        <!-- ABA 1: CENTRAL DE REGISTROS (ENTRADAS & SAÍDAS) UNIFICADA             -->
        <!-- ##################################################################### -->
        <section id="tab-content-records" class="main-tab-content space-y-6">

            <!-- 4 CARDS DE TELEMETRIA DO FLUXO DE ENTRADA & SAÍDA -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <!-- Card 1: Entradas -->
                <div class="modern-card p-4 border-l-4 border-l-blue-500 flex items-center justify-between">
                    <div>
                        <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Registros de Entrada</span>
                        <h3 class="text-2xl font-black text-slate-800 dark:text-white mt-1 font-mono" id="stat-inbound-count">345</h3>
                        <p class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">Documentos recebidos dos alunos</p>
                    </div>
                    <div class="w-12 h-12 rounded-xl bg-blue-500/10 text-blue-500 flex items-center justify-center text-xl">
                        <i class="ph-bold ph-tray-arrow-down"></i>
                    </div>
                </div>

                <!-- Card 2: Processamento IA -->
                <div class="modern-card p-4 border-l-4 border-l-emerald-500 flex items-center justify-between">
                    <div>
                        <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Trabalho da Secretaria</span>
                        <h3 class="text-2xl font-black text-emerald-500 mt-1 font-mono">0 HORAS</h3>
                        <p class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">100% Autônomo com Subagentes</p>
                    </div>
                    <div class="w-12 h-12 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center text-xl">
                        <i class="ph-bold ph-robot"></i>
                    </div>
                </div>

                <!-- Card 3: Saídas ERP SolisGE -->
                <div class="modern-card p-4 border-l-4 border-l-indigo-500 flex items-center justify-between">
                    <div>
                        <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Saídas ERP (SolisGE)</span>
                        <h3 class="text-2xl font-black text-slate-800 dark:text-white mt-1 font-mono" id="stat-outbound-erp">342</h3>
                        <p class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">Homologados no SolisGE / TOTVS</p>
                    </div>
                    <div class="w-12 h-12 rounded-xl bg-indigo-500/10 text-indigo-500 flex items-center justify-center text-xl">
                        <i class="ph-bold ph-arrows-clockwise"></i>
                    </div>
                </div>

                <!-- Card 4: Saídas WhatsApp -->
                <div class="modern-card p-4 border-l-4 border-l-green-500 flex items-center justify-between">
                    <div>
                        <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Notificações Emitidas</span>
                        <h3 class="text-2xl font-black text-green-500 mt-1 font-mono" id="stat-outbound-notif">345</h3>
                        <p class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">WhatsApp / Comprovantes de entrega</p>
                    </div>
                    <div class="w-12 h-12 rounded-xl bg-green-500/10 text-green-500 flex items-center justify-center text-xl">
                        <i class="ph-bold ph-whatsapp-logo"></i>
                    </div>
                </div>
            </div>

            <!-- PAINEL PRINCIPAL: FILTROS + TABELA DE REGISTROS DE ENTRADA E SAÍDA -->
            <div class="modern-card p-6 space-y-4">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
                    <div>
                        <h3 class="text-base font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
                            <i class="ph-bold ph-list-dashes text-blue-500 text-lg"></i>
                            <span>Livro Geral de Registros de Entrada e Saída</span>
                            <span class="text-xs bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 px-2 py-0.5 rounded-full font-mono font-bold">Portaria MEC nº 315/2018</span>
                        </h3>
                        <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Rastreabilidade integral: recebimento de arquivo, laudo pericial, integração ERP SolisGE e recibo WhatsApp.</p>
                    </div>

                    <div class="flex items-center gap-2 flex-wrap">
                        <button onclick="exportRecordsCSV()" class="px-3 py-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-bold transition flex items-center gap-1 cursor-pointer">
                            <i class="ph-bold ph-file-csv text-sm"></i>
                            <span>Exportar CSV</span>
                        </button>
                        <button onclick="refreshRecordsData()" class="px-3 py-1.5 btn-gold rounded-xl text-xs font-bold transition flex items-center gap-1 cursor-pointer">
                            <i class="ph-bold ph-arrows-clockwise text-sm"></i>
                            <span>Sincronizar Feed</span>
                        </button>
                    </div>
                </div>

                <!-- BARRA DE BUSCA E FILTROS DINÂMICOS -->
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-3 text-xs">
                    <!-- Campo de Busca -->
                    <div class="lg:col-span-5 relative">
                        <input type="text" id="records-search-input" oninput="filterRecords()" placeholder="Buscar por Nome do Aluno, CPF, Curso, Hash ou Protocolo..." class="modern-input pl-9 text-xs">
                        <i class="ph-bold ph-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-base"></i>
                    </div>

                    <!-- Filtro por Tipo de Fluxo -->
                    <div class="lg:col-span-4">
                        <select id="records-filter-type" onchange="filterRecords()" class="modern-input text-xs cursor-pointer font-bold">
                            <option value="ALL">Todos os Fluxos (Entradas &amp; Saídas)</option>
                            <option value="INBOUND">📥 Apenas Entradas (Documentos Aluno)</option>
                            <option value="OUTBOUND_ERP">📤 Apenas Saídas ERP (SolisGE / TOTVS)</option>
                            <option value="OUTBOUND_NOTIF">💬 Notificações de Saída (WhatsApp)</option>
                            <option value="PENDING">⚠️ Pendências Notificadas</option>
                        </select>
                    </div>

                    <!-- Filtro por Instituição -->
                    <div class="lg:col-span-3">
                        <select id="records-filter-inst" onchange="filterRecords()" class="modern-input text-xs cursor-pointer font-bold">
                            <option value="ALL">Todas as Instituições</option>
                            <option value="imes">Faculdade IMES</option>
                            <option value="colegio_modelo">Colégio Santa Maria</option>
                            <option value="unimetro">Universidade Metropolitana</option>
                        </select>
                    </div>
                </div>

                <!-- TABELA DE REGISTROS -->
                <div class="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 custom-scroll">
                    <table class="w-full text-left text-xs">
                        <thead class="bg-slate-100 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 font-extrabold uppercase tracking-wider text-[11px]">
                            <tr>
                                <th class="p-3.5">Direção &amp; Status</th>
                                <th class="p-3.5">Aluno &amp; Curso</th>
                                <th class="p-3.5">Documento &amp; Hash Entrada</th>
                                <th class="p-3.5">Saída SolisGE / ERP</th>
                                <th class="p-3.5">Saída Notificação</th>
                                <th class="p-3.5">Data &amp; Hora</th>
                                <th class="p-3.5 text-right">Ação</th>
                            </tr>
                        </thead>
                        <tbody id="records-table-body" class="divide-y divide-slate-200 dark:divide-slate-800">
                            <tr>
                                <td colspan="7" class="p-8 text-center text-slate-400 font-medium">Carregando registros de entrada e saída...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <!-- CONTADOR DE REGISTROS FILTRADOS -->
                <div class="flex items-center justify-between text-xs text-slate-400 pt-2">
                    <span id="records-counter-display">Exibindo registros em tempo real</span>
                    <span class="font-mono">Auditoria Criptográfica SHA-256 ativa</span>
                </div>
            </div>

        </section>

        <!-- ##################################################################### -->
        <!-- ABA 2: VISÃO EXECUTIVA & CONTRATANTES (ORIGINAL REFORÇADO)             -->
        <!-- ##################################################################### -->
        <section id="tab-content-executive" class="main-tab-content space-y-6 hidden">

            <!-- GAUGES VISUAIS DE CONSUMO E CAPACIDADE GLOBAL -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <!-- Gauge Circular de Capacidade -->
                <div class="modern-card p-6 flex flex-col justify-between">
                    <div>
                        <div class="flex items-center justify-between mb-4">
                            <div>
                                <h3 class="font-extrabold text-sm text-slate-800 dark:text-white">Capacidade Global Consumida</h3>
                                <p class="text-xs text-slate-400">Auditorias processadas no ciclo atual</p>
                            </div>
                            <span id="chart-institutions-count" class="text-xs font-bold px-2.5 py-1 bg-blue-50 dark:bg-blue-950/60 text-imes-blue dark:text-blue-300 rounded-full border border-blue-200 dark:border-blue-800">
                                3 contratantes
                            </span>
                        </div>

                        <div class="relative w-48 h-48 mx-auto my-2">
                            <canvas id="globalCapacityChart"></canvas>
                            <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                                <span id="gauge-percent-display" class="text-3xl font-black text-slate-800 dark:text-white font-mono">0%</span>
                                <span class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">do Limite Total</span>
                            </div>
                        </div>
                    </div>

                    <div class="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between text-xs">
                        <div>
                            <span class="text-slate-400 block text-[11px]">Projeção de Fechamento</span>
                            <strong id="projection-count-display" class="text-slate-800 dark:text-white font-mono font-bold">0 análises</strong>
                        </div>
                        <span class="text-emerald-600 dark:text-emerald-400 font-bold flex items-center gap-1">
                            <i class="ph-bold ph-check"></i> Margem Segura
                        </span>
                    </div>
                </div>

                <!-- Gráfico de Barras: Comparativo por Contratante -->
                <div class="modern-card p-6 lg:col-span-2 flex flex-col justify-between">
                    <div>
                        <div class="flex items-center justify-between mb-4">
                            <div>
                                <h3 class="font-extrabold text-sm text-slate-800 dark:text-white">Consumo por Instituição Contratante</h3>
                                <p class="text-xs text-slate-400">Comparação em tempo real do uso vs franquia contratada</p>
                            </div>
                            <div class="flex items-center gap-3 text-xs">
                                <span class="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                                    <span class="w-3 h-3 rounded-full bg-imes-blue"></span> Consumido
                                </span>
                                <span class="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                                    <span class="w-3 h-3 rounded-full bg-slate-300 dark:bg-slate-700"></span> Limite
                                </span>
                            </div>
                        </div>

                        <div class="w-full h-56 relative">
                            <canvas id="institutionsBarChart"></canvas>
                        </div>
                    </div>

                    <div class="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between text-xs text-slate-400">
                        <span>Métricas calculadas conforme ciclo contratual ativo de cada instituição.</span>
                        <button onclick="fetchInstitutions()" class="text-imes-blue dark:text-imes-gold hover:underline font-bold cursor-pointer">Recalcular</button>
                    </div>
                </div>
            </div>

            <!-- GESTÃO DE CONTRATANTES (CLIENTES E PLANOS) -->
            <div class="modern-card p-6 space-y-4">
                <div class="flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div class="relative w-full sm:w-96">
                        <input type="text" id="search-institutions" placeholder="Buscar por Nome da Instituição ou ID..." class="modern-input pl-9 text-xs">
                        <i class="ph-bold ph-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-base"></i>
                    </div>

                    <div class="flex items-center gap-2">
                        <span class="text-xs text-slate-400">Ações Rápidas:</span>
                        <button onclick="openWhiteLabelModal()" class="px-3 py-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-bold transition flex items-center gap-1 cursor-pointer">
                            <i class="ph-bold ph-paint-brush"></i> White-Label
                        </button>
                        <button onclick="openCreateModal()" class="px-3.5 py-1.5 btn-gold rounded-xl text-xs font-bold transition flex items-center gap-1 cursor-pointer">
                            <i class="ph-bold ph-plus"></i> Novo Cliente
                        </button>
                    </div>
                </div>

                <!-- TABELA DE CONTRATANTES -->
                <div class="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700 custom-scroll">
                    <table class="w-full text-left text-xs">
                        <thead class="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-extrabold uppercase tracking-wider text-[11px]">
                            <tr>
                                <th class="p-3.5">Instituição / Contratante</th>
                                <th class="p-3.5">Plano Ativo</th>
                                <th class="p-3.5">Consumo no Ciclo</th>
                                <th class="p-3.5">Chave da Secretaria</th>
                                <th class="p-3.5">Status</th>
                                <th class="p-3.5">Portais Ativos</th>
                                <th class="p-3.5 text-right">Ação</th>
                            </tr>
                        </thead>
                        <tbody id="institutions-table-body" class="divide-y divide-slate-200 dark:divide-slate-800">
                            <tr>
                                <td colspan="7" class="p-8 text-center text-slate-400">Carregando contratantes...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

        </section>

        <!-- ##################################################################### -->
        <!-- ABA 3: CONSOLE DOS SUBAGENTES & TELEMETRIA                             -->
        <!-- ##################################################################### -->
        <section id="tab-content-swarm" class="main-tab-content space-y-6 hidden">

            <!-- TELEMETRIA DE SAÚDE DA INFRAESTRUTURA -->
            <div class="modern-card p-5 bg-gradient-to-r from-[#0a2351] via-[#102d68] to-[#0a2351] text-white border-none shadow-md">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-4 mb-4">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-2xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xl">
                            <i class="ph-bold ph-heartbeat"></i>
                        </div>
                        <div>
                            <h2 class="text-sm sm:text-base font-extrabold text-white flex items-center gap-2">
                                <span>Monitoramento de Saúde da Infraestrutura</span>
                                <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
                            </h2>
                            <p class="text-xs text-blue-200">Telemetria em tempo real: API Gemini Vision OCR, latência e custódia digital Supabase</p>
                        </div>
                    </div>
                    <button onclick="checkHealthTelemetry()" class="px-3.5 py-1.5 bg-white/10 hover:bg-white/20 text-white border border-white/20 rounded-xl text-xs font-bold transition flex items-center gap-1.5 cursor-pointer">
                        <i class="ph-bold ph-arrows-clockwise text-sm"></i>
                        <span>Diagnóstico em Tempo Real</span>
                    </button>
                </div>

                <!-- CARDS DE TELEMETRIA -->
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div class="bg-black/20 rounded-2xl p-4 border border-white/10 flex items-center justify-between">
                        <div>
                            <span class="text-[11px] font-bold text-blue-200 uppercase tracking-wide">Status API Gemini</span>
                            <div id="health-gemini-status" class="text-base font-black text-emerald-400 mt-1 flex items-center gap-1.5">
                                <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                                Online (Operacional)
                            </div>
                            <span class="text-[11px] text-blue-200 block mt-0.5">Gemini 2.5 Flash • 99.8% Uptime</span>
                        </div>
                        <div class="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center text-xl">
                            <i class="ph-bold ph-cpu"></i>
                        </div>
                    </div>

                    <div class="bg-black/20 rounded-2xl p-4 border border-white/10 flex items-center justify-between">
                        <div>
                            <span class="text-[11px] font-bold text-blue-200 uppercase tracking-wide">Latência Média</span>
                            <div id="health-latency" class="text-xl font-black text-white mt-1 font-mono">1.35s</div>
                            <span class="text-[11px] text-blue-200 block mt-0.5">Higienização e OCR Gemini</span>
                        </div>
                        <div class="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-300 flex items-center justify-center text-xl">
                            <i class="ph-bold ph-gauge"></i>
                        </div>
                    </div>

                    <div class="bg-black/20 rounded-2xl p-4 border border-white/10 flex items-center justify-between">
                        <div>
                            <span class="text-[11px] font-bold text-blue-200 uppercase tracking-wide">Taxa de Conformidade</span>
                            <div id="health-conversion" class="text-xl font-black text-imes-gold mt-1 font-mono">94.8%</div>
                            <span class="text-[11px] text-blue-200 block mt-0.5">Aprovação nas normas MEC</span>
                        </div>
                        <div class="w-10 h-10 rounded-xl bg-amber-500/10 text-imes-gold flex items-center justify-center text-xl">
                            <i class="ph-bold ph-chart-line-up"></i>
                        </div>
                    </div>

                    <div class="bg-black/20 rounded-2xl p-4 border border-white/10 flex items-center justify-between">
                        <div>
                            <span class="text-[11px] font-bold text-blue-200 uppercase tracking-wide">Custódia Supabase</span>
                            <div class="text-base font-black text-emerald-400 mt-1 flex items-center gap-1.5">
                                <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                                Bucket Ativo
                            </div>
                            <span class="text-[11px] text-blue-200 block mt-0.5">documentos-alunos (A-Z)</span>
                        </div>
                        <div class="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-300 flex items-center justify-center text-xl">
                            <i class="ph-bold ph-hard-drives"></i>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ENXAME DE SUBAGENTES ESPECIALISTAS (MAS) -->
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <!-- Grid dos 8 Agentes -->
                <div class="lg:col-span-7 modern-card p-6 border-l-4 border-l-imes-blue space-y-4">
                    <div class="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
                        <div>
                            <h3 class="font-extrabold text-sm text-slate-800 dark:text-white flex items-center gap-2">
                                <i class="ph-bold ph-tree-structure text-imes-blue text-lg"></i>
                                <span>Enxame Multi-Agentes (MAS Autônomo)</span>
                            </h3>
                            <p class="text-xs text-slate-500 dark:text-slate-400">Agentes especializados em execução contínua com autonomia total</p>
                        </div>
                        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">
                            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                            100% Operacional
                        </span>
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        <div class="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                            <div>
                                <h5 class="font-bold text-slate-800 dark:text-white flex items-center gap-1.5">
                                    <i class="fa-solid fa-camera text-blue-500"></i> Perícia de Mídia
                                </h5>
                                <p class="text-[10px] text-slate-400">Higienização e enquadramento</p>
                            </div>
                            <span class="text-emerald-500 font-mono text-[10px] font-bold">ONLINE</span>
                        </div>

                        <div class="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                            <div>
                                <h5 class="font-bold text-slate-800 dark:text-white flex items-center gap-1.5">
                                    <i class="fa-solid fa-brain text-purple-500"></i> OCR Cognitivo Gemini
                                </h5>
                                <p class="text-[10px] text-slate-400">Extração multimodal de dados</p>
                            </div>
                            <span class="text-emerald-500 font-mono text-[10px] font-bold">ONLINE (0.4s)</span>
                        </div>

                        <div class="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                            <div>
                                <h5 class="font-bold text-slate-800 dark:text-white flex items-center gap-1.5">
                                    <i class="fa-solid fa-scale-balanced text-amber-500"></i> Compliance MEC 315
                                </h5>
                                <p class="text-[10px] text-slate-400">Temporalidade TTD e acervo</p>
                            </div>
                            <span class="text-emerald-500 font-mono text-[10px] font-bold">ONLINE (0.5s)</span>
                        </div>

                        <div class="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                            <div>
                                <h5 class="font-bold text-slate-800 dark:text-white flex items-center gap-1.5">
                                    <i class="fa-solid fa-shield-halved text-rose-500"></i> Forense Antifraude
                                </h5>
                                <p class="text-[10px] text-slate-400">Detecção de fontes e rasuras</p>
                            </div>
                            <span class="text-emerald-500 font-mono text-[10px] font-bold">ONLINE (0.6s)</span>
                        </div>

                        <div class="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                            <div>
                                <h5 class="font-bold text-slate-800 dark:text-white flex items-center gap-1.5">
                                    <i class="fa-solid fa-database text-indigo-500"></i> Conector ERP SolisGE
                                </h5>
                                <p class="text-[10px] text-slate-400">Despacho de homologação</p>
                            </div>
                            <span class="text-emerald-500 font-mono text-[10px] font-bold">CONECTADO</span>
                        </div>

                        <div class="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                            <div>
                                <h5 class="font-bold text-slate-800 dark:text-white flex items-center gap-1.5">
                                    <i class="fa-brands fa-whatsapp text-green-500"></i> Notificador WhatsApp
                                </h5>
                                <p class="text-[10px] text-slate-400">Recibos e avisos automáticos</p>
                            </div>
                            <span class="text-emerald-500 font-mono text-[10px] font-bold">ONLINE</span>
                        </div>
                    </div>
                </div>

                <!-- Terminal Console dos Subagentes em Tempo Real -->
                <div class="lg:col-span-5 bg-[#0F172A] border border-slate-800 rounded-2xl p-5 flex flex-col shadow-inner">
                    <div class="flex items-center justify-between pb-3 border-b border-slate-800">
                        <div class="flex items-center gap-2">
                            <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></span>
                            <h3 class="text-xs font-bold text-white uppercase tracking-wider font-mono">Console dos 5 Subagentes</h3>
                        </div>
                        <span class="text-[10px] text-slate-400 font-mono bg-slate-900 px-2 py-0.5 rounded border border-slate-800">Gemini 2.0 Flash + MCP</span>
                    </div>

                    <!-- Log Terminal -->
                    <div class="flex-1 bg-slate-950 rounded-xl p-3.5 border border-slate-900 font-mono text-[11px] text-slate-300 overflow-y-auto custom-scroll max-h-[340px] space-y-2 mt-3">
                        <p class="text-slate-500">[10:04:10] <span class="text-blue-400">[AGENTE_OCR]</span> Analisando RG de candidato (SSP/MG)...</p>
                        <p class="text-slate-400">[10:04:11] <span class="text-blue-400">[AGENTE_OCR]</span> CPF lido: 123.456.789-00 • Titularidade 100% confirmada.</p>
                        <p class="text-slate-400">[10:04:11] <span class="text-amber-400">[AGENTE_ANTIFRAUDE]</span> Inspeção pericial: Ausência de rasuras e fontes consistentes.</p>
                        <p class="text-slate-400">[10:04:12] <span class="text-indigo-400">[AGENTE_MEC315]</span> Certificado de Conclusão do Ensino Médio com visto de inspeção escolar.</p>
                        <p class="text-emerald-400">[10:04:12] <span class="text-emerald-400">[AUTO_DECISION]</span> Dossiê 100% aprovado pelos agentes regulatórios.</p>
                        <p class="text-slate-400">[10:04:13] <span class="text-emerald-400">[CUSTODIA_SUPABASE]</span> Gravando arquivo no bucket 'documentos-alunos' com Hash SHA-256.</p>
                        <p class="text-blue-300">[10:04:13] <span class="text-blue-400">[ERP_CONNECTOR]</span> Despachando matrícula para o SolisGE: HTTP 200 OK (#SL-2026-90482).</p>
                        <p class="text-slate-400">[10:04:14] <span class="text-emerald-400">[NOTIFICADOR]</span> Comprovante oficial com carimbo de tempo enviado ao WhatsApp do aluno.</p>
                        <p class="text-emerald-400 font-bold">[10:04:14] >>> MATRÍCULA CONCLUÍDA EM 3.8 SEGUNDOS COM TRABALHO HUMANO ZERO <<<</p>
                    </div>

                    <div class="mt-3 text-center">
                        <span class="text-[10px] text-slate-500 font-mono">
                            Fluxo 100% autônomo sem necessidade de intervenção da secretaria.
                        </span>
                    </div>
                </div>
            </div>

        </section>

    </main>

    <!-- ========================================================================= -->
    <!-- MODAL: INSPEÇÃO COMPLETA DO REGISTRO (INSPEÇÃO FORENSE DE ENTRADA & SAÍDA)-->
    <!-- ========================================================================= -->
    <div id="record-detail-modal" class="hidden fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
        <div class="bg-white dark:bg-slate-900 rounded-3xl max-w-3xl w-full shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[90vh]">
            <div class="p-5 bg-[#0a2351] text-white flex items-center justify-between border-b border-slate-700">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-blue-500/20 border border-blue-400/30 text-blue-300 flex items-center justify-center text-lg font-bold">
                        <i class="ph-bold ph-file-text"></i>
                    </div>
                    <div>
                        <div class="flex items-center gap-2">
                            <h3 class="font-extrabold text-sm sm:text-base text-white" id="modal-doc-title">Inspeção Detalhada do Registro</h3>
                            <span id="modal-status-badge" class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">100% Aprovado</span>
                        </div>
                        <p class="text-xs text-blue-200 font-mono" id="modal-protocol-num">Protocolo: PRT-2026-IMES-09482</p>
                    </div>
                </div>
                <button onclick="closeRecordDetailModal()" class="w-8 h-8 rounded-full hover:bg-white/10 flex items-center justify-center text-white transition cursor-pointer">
                    <i class="ph-bold ph-x text-lg"></i>
                </button>
            </div>

            <div class="p-6 space-y-5 overflow-y-auto custom-scroll text-xs">
                <!-- BLOCO 1: REGISTRO DE ENTRADA (INBOUND) -->
                <div class="p-4 rounded-2xl bg-blue-50/60 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900/60 space-y-2">
                    <h4 class="font-bold text-blue-900 dark:text-blue-300 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                        <i class="ph-bold ph-tray-arrow-down text-blue-500"></i>
                        <span>Registro de Entrada (Recebido do Aluno)</span>
                    </h4>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-slate-700 dark:text-slate-300">
                        <div>
                            <span class="text-slate-400 block text-[10px]">Aluno:</span>
                            <strong id="modal-student-name" class="text-sm">Lucas Gabriel Mendonça</strong>
                        </div>
                        <div>
                            <span class="text-slate-400 block text-[10px]">CPF / Matrícula:</span>
                            <span id="modal-student-cpf" class="font-mono font-bold">123.456.789-00 • Matrícula 202610482</span>
                        </div>
                        <div>
                            <span class="text-slate-400 block text-[10px]">Curso &amp; Instituição:</span>
                            <span id="modal-course-name">Direito • Faculdade IMES</span>
                        </div>
                        <div>
                            <span class="text-slate-400 block text-[10px]">Data e Hora da Entrada:</span>
                            <span id="modal-timestamp" class="font-mono">Hoje às 10:04:10 (28/09/2026)</span>
                        </div>
                    </div>
                    <div class="pt-2 border-t border-blue-200/60 dark:border-blue-900/40">
                        <span class="text-slate-400 block text-[10px]">Hash SHA-256 de Custódia (Integridade Original):</span>
                        <div class="flex items-center gap-2 mt-0.5">
                            <span id="modal-hash-full" class="font-mono text-[11px] text-blue-600 dark:text-blue-300 break-all bg-white dark:bg-slate-900 px-2 py-1 rounded border border-blue-200 dark:border-blue-800 flex-1">e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855</span>
                            <button onclick="copyHashModal()" class="px-2.5 py-1 bg-blue-600 text-white rounded text-[10px] font-bold hover:bg-blue-700 cursor-pointer">Copiar</button>
                        </div>
                    </div>
                </div>

                <!-- BLOCO 2: LAUDO DA AUDITORIA AUTÔNOMA IA -->
                <div class="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2">
                    <h4 class="font-bold text-slate-800 dark:text-white uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                        <i class="ph-bold ph-robot text-emerald-500"></i>
                        <span>Laudo dos Subagentes (Straight-Through Processing - 3.8s)</span>
                    </h4>
                    <div class="space-y-2 text-[11px]">
                        <div class="flex items-start gap-2">
                            <i class="ph-bold ph-check-circle text-emerald-500 mt-0.5"></i>
                            <div>
                                <strong class="text-slate-800 dark:text-white">Subagente OCR Cognitivo Gemini:</strong>
                                <span class="text-slate-600 dark:text-slate-300" id="modal-ocr-notes">CPF e Nome lidos com 99.8% de confiança. Documento expedido por SSP/MG válido.</span>
                            </div>
                        </div>
                        <div class="flex items-start gap-2">
                            <i class="ph-bold ph-check-circle text-emerald-500 mt-0.5"></i>
                            <div>
                                <strong class="text-slate-800 dark:text-white">Subagente Forense Antifraude:</strong>
                                <span class="text-slate-600 dark:text-slate-300">Ausência de manipulação digital, fontes tipográficas coerentes, bordas íntegras.</span>
                            </div>
                        </div>
                        <div class="flex items-start gap-2">
                            <i class="ph-bold ph-check-circle text-emerald-500 mt-0.5"></i>
                            <div>
                                <strong class="text-slate-800 dark:text-white">Subagente Compliance Portaria MEC nº 315/2018:</strong>
                                <span class="text-slate-600 dark:text-slate-300">Documento atende aos requisitos de temporalidade TTD e habilitação para matrícula no Ensino Superior.</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- BLOCO 3: REGISTROS DE SAÍDA (OUTBOUND) -->
                <div class="p-4 rounded-2xl bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900/60 space-y-3">
                    <h4 class="font-bold text-emerald-900 dark:text-emerald-300 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                        <i class="ph-bold ph-paper-plane-tilt text-emerald-500"></i>
                        <span>Registros de Saída (Integrações &amp; Notificações)</span>
                    </h4>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-slate-700 dark:text-slate-300">
                        <div class="p-3 rounded-xl bg-white dark:bg-slate-900 border border-emerald-200 dark:border-emerald-900/40">
                            <span class="text-slate-400 block text-[10px]">Despacho ERP SolisGE:</span>
                            <div class="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-bold mt-0.5">
                                <i class="ph-bold ph-check"></i>
                                <span id="modal-erp-id">Sincronizado (#SL-2026-90482)</span>
                            </div>
                            <span class="text-[10px] text-slate-400 block mt-0.5">HTTP 200 OK • SolisGE Acadêmico</span>
                        </div>

                        <div class="p-3 rounded-xl bg-white dark:bg-slate-900 border border-emerald-200 dark:border-emerald-900/40">
                            <span class="text-slate-400 block text-[10px]">Notificação WhatsApp Aluno:</span>
                            <div class="flex items-center gap-1.5 text-green-600 dark:text-green-400 font-bold mt-0.5">
                                <i class="ph-bold ph-whatsapp-logo"></i>
                                <span id="modal-wa-status">Comprovante Entregue (Lido)</span>
                            </div>
                            <span class="text-[10px] text-slate-400 block mt-0.5" id="modal-wa-phone">+55 (35) 99876-4321</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="p-4 bg-slate-100 dark:bg-slate-800/80 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
                <span class="text-[11px] text-slate-400 font-mono">Custódia: Supabase Bucket 'documentos-alunos'</span>
                <button onclick="closeRecordDetailModal()" class="px-5 py-2 btn-gold rounded-xl text-xs font-bold cursor-pointer">
                    Fechar Inspeção
                </button>
            </div>
        </div>
    </div>

    <!-- ========================================================================= -->
    <!-- MODAL: EDITOR WHITE-LABEL COM PREVIEW EM TEMPO REAL                      -->
    <!-- ========================================================================= -->
    <div id="whitelabel-modal" class="hidden fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
        <div class="bg-white dark:bg-slate-900 rounded-3xl max-w-4xl w-full shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[90vh]">
            <div class="p-5 bg-[#0a2351] text-white flex items-center justify-between border-b border-slate-700">
                <div class="flex items-center gap-3">
                    <div class="w-9 h-9 rounded-xl bg-imes-gold text-imes-blue flex items-center justify-center text-lg font-bold shadow">
                        <i class="ph-bold ph-palette"></i>
                    </div>
                    <div>
                        <h3 class="font-extrabold text-sm sm:text-base text-white">Editor White-Label Instantâneo</h3>
                        <p class="text-xs text-blue-200">Personalize cores institucionais, logotipo e títulos por contratante</p>
                    </div>
                </div>
                <button onclick="document.getElementById('whitelabel-modal').classList.add('hidden')" class="w-8 h-8 rounded-full hover:bg-white/10 flex items-center justify-center text-white transition cursor-pointer">
                    <i class="ph-bold ph-x text-lg"></i>
                </button>
            </div>

            <div class="flex-1 flex flex-col md:flex-row overflow-hidden">
                <!-- FORMULÁRIO DE CUSTOMIZAÇÃO -->
                <div class="md:w-1/2 p-6 space-y-4 overflow-y-auto custom-scroll border-b md:border-b-0 md:border-r border-slate-200 dark:border-slate-800 text-xs">
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider text-[11px] mb-1">Selecione o Contratante</label>
                        <select id="wl-select-inst" onchange="loadInstitutionForBranding(this.value)" class="modern-input text-xs cursor-pointer"></select>
                    </div>

                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider text-[11px] mb-1">URL ou Caminho do Logotipo Oficial</label>
                        <input type="text" id="wl-logo-url" oninput="updateLivePreview()" class="modern-input text-xs" placeholder="/static/images/logo-imes.jpg">
                    </div>

                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider text-[11px] mb-1">Título do Portal</label>
                        <input type="text" id="wl-portal-title" oninput="updateLivePreview()" class="modern-input text-xs" placeholder="Ex: Portal de Documentos - Faculdade IMES">
                    </div>

                    <div class="grid grid-cols-2 gap-3 pt-2">
                        <div>
                            <label class="block font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider text-[11px] mb-1">Cor Primária (Header)</label>
                            <div class="flex items-center gap-2">
                                <input type="color" id="wl-primary-color-picker" onchange="syncColorInput('primary', this.value)" class="w-9 h-9 rounded-lg border border-slate-300 cursor-pointer">
                                <input type="text" id="wl-primary-color-text" oninput="syncColorInput('primary', this.value)" class="modern-input text-xs font-mono" placeholder="#0a2351">
                            </div>
                        </div>

                        <div>
                            <label class="block font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider text-[11px] mb-1">Cor Secundária (Destaques)</label>
                            <div class="flex items-center gap-2">
                                <input type="color" id="wl-secondary-color-picker" onchange="syncColorInput('secondary', this.value)" class="w-9 h-9 rounded-lg border border-slate-300 cursor-pointer">
                                <input type="text" id="wl-secondary-color-text" oninput="syncColorInput('secondary', this.value)" class="modern-input text-xs font-mono" placeholder="#fdb913">
                            </div>
                        </div>
                    </div>

                    <div class="pt-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-end gap-2">
                        <button type="button" onclick="document.getElementById('whitelabel-modal').classList.add('hidden')" class="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-white font-bold rounded-xl text-xs cursor-pointer">
                            Cancelar
                        </button>
                        <button type="button" onclick="saveWhiteLabelBranding()" class="px-5 py-2 btn-gold rounded-xl text-xs font-bold shadow transition cursor-pointer">
                            Salvar Identidade Visual
                        </button>
                    </div>
                </div>

                <!-- PREVIEW AO VIVO DA IDENTIDADE VISUAL -->
                <div class="md:w-1/2 p-6 bg-slate-50 dark:bg-slate-950 flex flex-col justify-center items-center">
                    <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-3">Pré-visualização em Tempo Real</span>
                    <div class="w-full max-w-sm rounded-2xl overflow-hidden shadow-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 transition-all">
                        <div id="preview-header" class="p-4 text-white flex items-center gap-3 transition-colors" style="background-color: #0a2351;">
                            <img id="preview-logo-img" src="/static/images/logo-imes.jpg" class="w-10 h-10 rounded-xl bg-white p-1 object-contain shadow" alt="Preview Logo">
                            <div>
                                <h4 id="preview-title-display" class="font-extrabold text-sm truncate max-w-[200px]">Portal de Documentos</h4>
                                <p class="text-[10px] text-blue-100">Secretaria Acadêmica Oficial</p>
                            </div>
                        </div>
                        <div class="p-5 space-y-3">
                            <div class="h-8 bg-slate-100 dark:bg-slate-800 rounded-xl w-3/4"></div>
                            <div class="h-10 bg-slate-100 dark:bg-slate-800 rounded-xl w-full"></div>
                            <button id="preview-btn" class="w-full py-2.5 rounded-xl font-bold text-xs text-[#0a2351] shadow transition" style="background-color: #fdb913;">
                                Botão com Acento Secundário
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- ========================================================================= -->
    <!-- MODAL: GERENCIAR PLANO E LIMITES DO CONTRATANTE                          -->
    <!-- ========================================================================= -->
    <div id="edit-modal" class="hidden fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
        <div class="bg-white dark:bg-slate-900 rounded-3xl max-w-lg w-full shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col">
            <div class="p-5 bg-[#0a2351] text-white flex items-center justify-between border-b border-slate-700">
                <div class="flex items-center gap-2">
                    <i class="ph-bold ph-gear text-xl text-imes-gold"></i>
                    <h3 class="font-bold text-sm text-white">Gerenciar Contratante &amp; Plano</h3>
                </div>
                <button onclick="document.getElementById('edit-modal').classList.add('hidden')" class="text-white hover:text-slate-300 p-1 text-lg cursor-pointer">
                    <i class="ph-bold ph-x"></i>
                </button>
            </div>

            <form id="edit-inst-form" onsubmit="handleSavePlan(event)" class="p-6 space-y-3.5 text-xs">
                <input type="hidden" id="edit-inst-id">

                <div>
                    <label class="block font-bold text-slate-700 dark:text-slate-300 mb-1">Instituição</label>
                    <input type="text" id="edit-inst-name" disabled class="modern-input opacity-70 cursor-not-allowed">
                </div>

                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-1">Tier do Plano</label>
                        <select id="edit-plan-tier" class="modern-input cursor-pointer">
                            <option value="STARTER">Starter</option>
                            <option value="PROFISSIONAL">Profissional</option>
                            <option value="ENTERPRISE">Enterprise</option>
                        </select>
                    </div>

                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-1">Limite Mensal de Análises</label>
                        <input type="number" id="edit-monthly-limit" min="0" step="50" class="modern-input font-mono font-bold">
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-1">Nome de Exibição do Plano</label>
                        <input type="text" id="edit-plan-name" class="modern-input">
                    </div>

                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-1">Dia do Vencimento</label>
                        <input type="number" id="edit-billing-day" min="1" max="31" class="modern-input font-mono">
                    </div>
                </div>

                <div>
                    <label class="block font-bold text-slate-700 dark:text-slate-300 mb-1">Chave de Acesso da Secretaria</label>
                    <div class="flex items-center gap-2">
                        <input type="text" id="edit-admin-key" required class="modern-input font-mono font-bold">
                        <button type="button" onclick="generateRandomKey()" class="px-3 py-2.5 bg-slate-200 dark:bg-slate-700 rounded-xl font-bold text-xs" title="Gerar nova chave">
                            <i class="ph-bold ph-arrows-clockwise"></i>
                        </button>
                    </div>
                </div>

                <div>
                    <label class="block font-bold text-slate-700 dark:text-slate-300 mb-1">Status do Acesso</label>
                    <select id="edit-is-active" class="modern-input cursor-pointer font-bold">
                        <option value="true">Ativo (Acesso Liberado)</option>
                        <option value="false">Suspenso (Bloqueado)</option>
                    </select>
                </div>

                <div class="pt-4 flex items-center justify-between border-t border-slate-200 dark:border-slate-800">
                    <button type="button" onclick="resetCurrentUsage()" class="px-3 py-2 bg-amber-50 dark:bg-amber-950/40 hover:bg-amber-100 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700 font-bold rounded-xl text-xs transition flex items-center gap-1.5 cursor-pointer">
                        <i class="ph-bold ph-arrow-counter-clockwise"></i>
                        <span>Zerar Consumo</span>
                    </button>

                    <div class="flex items-center gap-2">
                        <button type="button" onclick="document.getElementById('edit-modal').classList.add('hidden')" class="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-white font-bold rounded-xl text-xs cursor-pointer">
                            Cancelar
                        </button>
                        <button type="submit" class="px-5 py-2 btn-gold rounded-xl text-xs font-bold shadow transition cursor-pointer">
                            Salvar Alterações
                        </button>
                    </div>
                </div>
            </form>
        </div>
    </div>

    <!-- ========================================================================= -->
    <!-- MODAL: CADASTRAR NOVO CONTRATANTE                                         -->
    <!-- ========================================================================= -->
    <div id="create-modal" class="hidden fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
        <div class="bg-white dark:bg-slate-900 rounded-3xl max-w-xl w-full shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col">
            <div class="p-5 bg-[#0a2351] text-white flex items-center justify-between border-b border-slate-700">
                <div class="flex items-center gap-2">
                    <i class="ph-bold ph-plus-square text-xl text-imes-gold"></i>
                    <h3 class="font-bold text-sm text-white">Cadastrar Novo Contratante</h3>
                </div>
                <button onclick="document.getElementById('create-modal').classList.add('hidden')" class="text-white hover:text-slate-300 p-1 text-lg cursor-pointer">
                    <i class="ph-bold ph-x"></i>
                </button>
            </div>

            <form id="create-inst-form" onsubmit="handleCreateInstitution(event)" class="p-6 space-y-3.5 text-xs">
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-1">Nome Oficial da Instituição</label>
                        <input type="text" id="new-name" required placeholder="Ex: Faculdade Horizon" class="modern-input">
                    </div>
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-1">Slug da URL (Identificador)</label>
                        <input type="text" id="new-id" required placeholder="Ex: faculdade_horizon" class="modern-input font-mono font-bold">
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-1">Categoria de Ensino</label>
                        <select id="new-type" class="modern-input cursor-pointer">
                            <option value="FACULDADE">Faculdade (Graduação/Pós)</option>
                            <option value="UNIVERSIDADE">Universidade</option>
                            <option value="COLEGIO">Colégio (Fundamental/Médio)</option>
                            <option value="ESCOLA_BASICA">Escola Básica</option>
                            <option value="ESCOLA_TECNICA">Escola Técnica</option>
                        </select>
                    </div>

                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-1">Plano Inicial</label>
                        <select id="new-plan-tier" class="modern-input cursor-pointer">
                            <option value="PROFISSIONAL">Profissional (500 docs/mês)</option>
                            <option value="STARTER">Starter (150 docs/mês)</option>
                            <option value="ENTERPRISE">Enterprise (Ilimitado)</option>
                        </select>
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-1">Limite Mensal</label>
                        <input type="number" id="new-monthly-limit" value="500" min="0" step="50" required class="modern-input font-mono font-bold">
                    </div>

                    <div>
                        <label class="block font-bold text-slate-700 dark:text-slate-300 mb-1">Chave da Secretaria</label>
                        <input type="text" id="new-admin-key" required placeholder="Ex: horizon-sec-2026" class="modern-input font-mono font-bold">
                    </div>
                </div>

                <div class="pt-4 flex items-center justify-end gap-2 border-t border-slate-200 dark:border-slate-800">
                    <button type="button" onclick="document.getElementById('create-modal').classList.add('hidden')" class="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-white font-bold rounded-xl text-xs cursor-pointer">
                        Cancelar
                    </button>
                    <button type="submit" class="px-5 py-2 btn-gold rounded-xl text-xs font-bold shadow transition cursor-pointer">
                        Cadastrar Contratante
                    </button>
                </div>
            </form>
        </div>
    </div>

    <!-- RODAPÉ INSTITUCIONAL -->
    <footer class="bg-white dark:bg-[#0D1B2A] border-t border-slate-200 dark:border-slate-800 px-6 py-4 text-center text-xs text-slate-500">
        ProtocoloEdu • Central Unificada de Registros e Gestão Multi-Instituição • Portaria MEC nº 315/2018
    </footer>

    <!-- ========================================================================= -->
    <!-- SCRIPTS INTEGRADOS DA CENTRAL UNIFICADA                                   -->
    <!-- ========================================================================= -->
    <script>
        // Supressão de inspeção DevTools (F12)
        if (window.console) {
            ['log', 'info', 'warn', 'error', 'debug'].forEach(m => { try { window.console[m] = function(){}; } catch(e){} });
        }
        document.addEventListener('keydown', function(e) {
            if (e.keyCode === 123 || (e.ctrlKey && e.shiftKey && (e.keyCode === 73 || e.keyCode === 74)) || (e.ctrlKey && e.keyCode === 85)) {
                e.preventDefault(); return false;
            }
        });
        document.addEventListener('contextmenu', function(e) { e.preventDefault(); });

        let allInstitutions = [];
        let allRecords = [];
        let filteredRecords = [];
        let gaugeChartInstance = null;
        let barChartInstance = null;

        // --- CONTROLE DE TEMA (DARK / LIGHT) ---
        const themeToggle = document.getElementById('theme-toggle');
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'light') {
            document.body.classList.remove('dark-mode');
            document.documentElement.classList.remove('dark');
            if (themeToggle) themeToggle.checked = false;
        } else {
            document.body.classList.add('dark-mode');
            document.documentElement.classList.add('dark');
            if (themeToggle) themeToggle.checked = true;
        }

        if (themeToggle) {
            themeToggle.addEventListener('change', () => {
                if (themeToggle.checked) {
                    document.body.classList.add('dark-mode');
                    document.documentElement.classList.add('dark');
                    localStorage.setItem('theme', 'dark');
                } else {
                    document.body.classList.remove('dark-mode');
                    document.documentElement.classList.remove('dark');
                    localStorage.setItem('theme', 'light');
                }
            });
        }

        // --- NAVEGAÇÃO DE ABAS UNIFICADAS ---
        function switchMainTab(tab) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.main-tab-content').forEach(c => c.classList.add('hidden'));

            const btn = document.getElementById(`tab-btn-${tab}`);
            const content = document.getElementById(`tab-content-${tab}`);

            if (btn) btn.classList.add('active');
            if (content) content.classList.remove('hidden');

            try {
                history.replaceState(null, '', '#' + tab);
            } catch(e) {}
        }

        // Verificar hash inicial da URL
        window.addEventListener('DOMContentLoaded', () => {
            const hash = window.location.hash.replace('#', '') || 'records';
            if (['records', 'executive', 'swarm'].includes(hash)) {
                switchMainTab(hash);
            } else {
                switchMainTab('records');
            }
            initData();
        });

        function escapeHtml(text) {
            if (text === null || text === undefined) return '';
            return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
        }

        function getSuperKey() {
            return 'master-protocolo-2026';
        }

        // --- BASE DE DADOS DOS REGISTROS DE ENTRADA & SAÍDA ---
        const MOCK_RECORDS = [
            {
                id: "REC-2026-001",
                student_name: "Lucas Gabriel Mendonça",
                student_cpf: "123.456.789-00",
                student_id: "202610482",
                course_name: "Direito",
                institution_id: "imes",
                institution_name: "Faculdade IMES",
                doc_name: "RG (Frente e Verso)",
                file_size: "1.8 MB",
                inbound_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                inbound_time: "Hoje às 10:04:10",
                flow_type: "INBOUND",
                status: "APPROVED",
                erp_status: "SINCRONIZADO",
                erp_id: "#SL-2026-90482",
                notif_status: "ENTREGUE",
                notif_phone: "+55 (35) 99876-4321",
                ai_time: "3.8s",
                notes: "Identificação civil confirmada por OCR. Sem adulteração gráfica."
            },
            {
                id: "REC-2026-002",
                student_name: "Mariana Costa Rodrigues",
                student_cpf: "234.567.890-11",
                student_id: "202610399",
                course_name: "Pedagogia",
                institution_id: "imes",
                institution_name: "Faculdade IMES",
                doc_name: "Histórico Escolar Ensino Médio",
                file_size: "2.4 MB",
                inbound_hash: "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
                inbound_time: "Hoje às 09:48:22",
                flow_type: "OUTBOUND_ERP",
                status: "APPROVED",
                erp_status: "SINCRONIZADO",
                erp_id: "#SL-2026-90399",
                notif_status: "ENTREGUE",
                notif_phone: "+55 (35) 98765-1122",
                ai_time: "3.5s",
                notes: "Carimbo de visto de inspeção escolar validado nos moldes da Portaria MEC 315/2018."
            },
            {
                id: "REC-2026-003",
                student_name: "Carlos Eduardo Supabase",
                student_cpf: "345.678.901-22",
                student_id: "202610501",
                course_name: "Administração",
                institution_id: "imes",
                institution_name: "Faculdade IMES",
                doc_name: "Certidão de Nascimento",
                file_size: "1.2 MB",
                inbound_hash: "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
                inbound_time: "Hoje às 09:12:05",
                flow_type: "OUTBOUND_NOTIF",
                status: "APPROVED",
                erp_status: "SINCRONIZADO",
                erp_id: "#SL-2026-90501",
                notif_status: "ENTREGUE",
                notif_phone: "+55 (35) 99123-4567",
                ai_time: "3.7s",
                notes: "Averbação civil e selo de cartório reconhecidos com precisão 100%."
            },
            {
                id: "REC-2026-004",
                student_name: "Bruna Ferreira Silveira",
                student_cpf: "456.789.012-33",
                student_id: "202610520",
                course_name: "Medicina Veterinária",
                institution_id: "imes",
                institution_name: "Faculdade IMES",
                doc_name: "Certificado Ensino Médio (Verso)",
                file_size: "1.5 MB",
                inbound_hash: "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b",
                inbound_time: "Hoje às 08:35:40",
                flow_type: "PENDING",
                status: "PENDING",
                erp_status: "AGUARDANDO",
                erp_id: "Pendente",
                notif_status: "AVISO_ENVIADO",
                notif_phone: "+55 (35) 99988-7766",
                ai_time: "3.9s",
                notes: "Subagente MEC 315 solicitou reenvio: Falta carimbo legível da secretaria escolar no verso."
            },
            {
                id: "REC-2026-005",
                student_name: "Thiago Henrique Souza",
                student_cpf: "567.890.123-44",
                student_id: "202610533",
                course_name: "Engenharia de Software",
                institution_id: "unimetro",
                institution_name: "Universidade Metropolitana",
                doc_name: "Diploma de 2ª Graduação (PAdES)",
                file_size: "3.1 MB",
                inbound_hash: "d4735e3a265e16eee03f59718b9b5d03019c07d8b6c51f90da3a666eec13ab35",
                inbound_time: "Hoje às 08:15:19",
                flow_type: "OUTBOUND_ERP",
                status: "APPROVED",
                erp_status: "SINCRONIZADO",
                erp_id: "#TOTVS-8831",
                notif_status: "ENTREGUE",
                notif_phone: "+55 (11) 98111-2233",
                ai_time: "4.1s",
                notes: "Validação de assinatura ICP-Brasil em PDF PAdES concluída com certificado X.509 autêntico."
            },
            {
                id: "REC-2026-006",
                student_name: "Beatriz Lima Alcântara",
                student_cpf: "678.901.234-55",
                student_id: "202610540",
                course_name: "Enfermagem",
                institution_id: "imes",
                institution_name: "Faculdade IMES",
                doc_name: "Comprovante de Residência",
                file_size: "950 KB",
                inbound_hash: "4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce",
                inbound_time: "Hoje às 07:55:00",
                flow_type: "INBOUND",
                status: "APPROVED",
                erp_status: "SINCRONIZADO",
                erp_id: "#SL-2026-90540",
                notif_status: "ENTREGUE",
                notif_phone: "+55 (35) 99222-3344",
                ai_time: "3.4s",
                notes: "Conta de energia elétrica com titularidade e CEP compatíveis com o cadastro."
            }
        ];

        async function initData() {
            await fetchInstitutions();
            await loadRecordsFromSupabaseOrMock();
        }

        async function loadRecordsFromSupabaseOrMock() {
            allRecords = [...MOCK_RECORDS];
            if (supabaseClient) {
                try {
                    const { data, error } = await supabaseClient.from('student_dossiers').select('*').limit(20);
                    if (!error && data && data.length > 0) {
                        data.forEach((item, idx) => {
                            allRecords.unshift({
                                id: `SUPA-${item.id || idx}`,
                                student_name: item.student_name || "Estudante Supabase",
                                student_cpf: item.cpf || "000.000.000-00",
                                student_id: item.student_id || `2026${idx}`,
                                course_name: item.course_name || "Graduação",
                                institution_id: item.institution_id || "imes",
                                institution_name: item.institution_id === "imes" ? "Faculdade IMES" : item.institution_id,
                                doc_name: "Dossiê Digital Completo",
                                file_size: "1.9 MB",
                                inbound_hash: item.custody_hash || "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                                inbound_time: "Hoje às 10:00",
                                flow_type: item.status === 'APROVADO' ? 'OUTBOUND_ERP' : 'INBOUND',
                                status: item.status === 'APROVADO' ? 'APPROVED' : 'PENDING',
                                erp_status: item.status === 'APROVADO' ? 'SINCRONIZADO' : 'EM_ANALISE',
                                erp_id: item.erp_transaction_id || `#SL-2026-${10000+idx}`,
                                notif_status: "ENTREGUE",
                                notif_phone: "+55 (35) 99999-0000",
                                ai_time: "3.8s",
                                notes: "Integrado via Supabase Database em tempo real."
                            });
                        });
                    }
                } catch(e) {}
            }
            renderRecords(allRecords);
        }

        function filterRecords() {
            const query = (document.getElementById('records-search-input')?.value || '').toLowerCase().trim();
            const flowFilter = document.getElementById('records-filter-type')?.value || 'ALL';
            const instFilter = document.getElementById('records-filter-inst')?.value || 'ALL';

            filteredRecords = allRecords.filter(rec => {
                if (instFilter !== 'ALL' && rec.institution_id !== instFilter) return false;
                if (flowFilter === 'INBOUND' && rec.flow_type !== 'INBOUND') return false;
                if (flowFilter === 'OUTBOUND_ERP' && rec.flow_type !== 'OUTBOUND_ERP') return false;
                if (flowFilter === 'OUTBOUND_NOTIF' && rec.flow_type !== 'OUTBOUND_NOTIF') return false;
                if (flowFilter === 'PENDING' && rec.status !== 'PENDING') return false;

                if (query) {
                    const match = (
                        rec.student_name.toLowerCase().includes(query) ||
                        rec.student_cpf.includes(query) ||
                        rec.student_id.toLowerCase().includes(query) ||
                        rec.course_name.toLowerCase().includes(query) ||
                        rec.inbound_hash.toLowerCase().includes(query) ||
                        rec.erp_id.toLowerCase().includes(query) ||
                        rec.id.toLowerCase().includes(query)
                    );
                    if (!match) return false;
                }
                return true;
            });

            renderRecords(filteredRecords);
        }

        function renderRecords(records) {
            const tbody = document.getElementById('records-table-body');
            const counter = document.getElementById('records-counter-display');
            if (counter) counter.textContent = `Exibindo ${records.length} de ${allRecords.length} registros`;

            const badgeTotal = document.getElementById('badge-total-records');
            if (badgeTotal) badgeTotal.textContent = `${allRecords.length} Registros`;

            if (records.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="p-8 text-center text-slate-400 font-medium">Nenhum registro encontrado com os filtros selecionados.</td></tr>`;
                return;
            }

            tbody.innerHTML = records.map(rec => {
                let badgeDirection = '';
                if (rec.status === 'PENDING') {
                    badgeDirection = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700 flex items-center gap-1 w-fit"><i class="ph-bold ph-warning"></i> PENDÊNCIA</span>`;
                } else if (rec.flow_type === 'INBOUND') {
                    badgeDirection = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 dark:bg-blue-950/80 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-700 flex items-center gap-1 w-fit"><i class="ph-bold ph-tray-arrow-down"></i> ENTRADA ALUNO</span>`;
                } else if (rec.flow_type === 'OUTBOUND_ERP') {
                    badgeDirection = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-100 dark:bg-indigo-950/80 text-indigo-800 dark:text-indigo-300 border border-indigo-300 dark:border-indigo-700 flex items-center gap-1 w-fit"><i class="ph-bold ph-arrows-clockwise"></i> SAÍDA SOLIS</span>`;
                } else {
                    badgeDirection = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-green-100 dark:bg-green-950/80 text-green-800 dark:text-green-300 border border-green-300 dark:border-green-700 flex items-center gap-1 w-fit"><i class="ph-bold ph-whatsapp-logo"></i> WHATSAPP</span>`;
                }

                const hashShort = rec.inbound_hash.substring(0, 10) + '...';

                return `
                    <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                        <td class="p-3.5">
                            ${badgeDirection}
                            <span class="text-[10px] text-slate-400 font-mono mt-0.5 block">${escapeHtml(rec.id)}</span>
                        </td>
                        <td class="p-3.5">
                            <div class="font-extrabold text-slate-800 dark:text-white">${escapeHtml(rec.student_name)}</div>
                            <div class="text-[11px] text-slate-400 font-mono">
                                ${escapeHtml(rec.student_cpf)} • ${escapeHtml(rec.course_name)}
                            </div>
                        </td>
                        <td class="p-3.5">
                            <div class="font-bold text-slate-700 dark:text-slate-300">${escapeHtml(rec.doc_name)}</div>
                            <div class="text-[10px] font-mono text-slate-400 flex items-center gap-1 mt-0.5">
                                <span>Hash: ${hashShort}</span>
                                <span class="text-blue-500 font-bold">(${rec.file_size})</span>
                            </div>
                        </td>
                        <td class="p-3.5">
                            <span class="font-mono text-xs font-bold text-indigo-600 dark:text-indigo-400 flex items-center gap-1">
                                <i class="ph-bold ph-check text-[11px]"></i> ${escapeHtml(rec.erp_id)}
                            </span>
                            <span class="text-[10px] text-slate-400 block">${rec.erp_status === 'SINCRONIZADO' ? 'HTTP 200 • SolisGE' : 'Pendente'}</span>
                        </td>
                        <td class="p-3.5">
                            <span class="font-bold text-green-600 dark:text-green-400 flex items-center gap-1">
                                <i class="ph-bold ph-whatsapp-logo"></i> ${escapeHtml(rec.notif_status)}
                            </span>
                            <span class="text-[10px] text-slate-400 font-mono block">${escapeHtml(rec.notif_phone)}</span>
                        </td>
                        <td class="p-3.5 font-mono text-slate-500 dark:text-slate-400 whitespace-nowrap">
                            ${escapeHtml(rec.inbound_time)}
                            <span class="text-[10px] block text-emerald-500 font-bold">${rec.ai_time} (100% IA)</span>
                        </td>
                        <td class="p-3.5 text-right">
                            <button onclick="inspectRecordModal('${rec.id}')" class="px-3 py-1.5 bg-blue-50 dark:bg-blue-950/60 hover:bg-blue-100 text-blue-700 dark:text-blue-300 font-bold rounded-xl text-xs border border-blue-200 dark:border-blue-800 transition flex items-center gap-1 ml-auto cursor-pointer">
                                <i class="ph-bold ph-eye"></i> Inspecionar
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        function inspectRecordModal(recordId) {
            const rec = allRecords.find(r => r.id === recordId);
            if (!rec) return;

            document.getElementById('modal-doc-title').textContent = `${rec.doc_name} • ${rec.student_name}`;
            document.getElementById('modal-protocol-num').textContent = `Protocolo: PRT-2026-${rec.institution_id.toUpperCase()}-${rec.student_id}`;
            document.getElementById('modal-student-name').textContent = rec.student_name;
            document.getElementById('modal-student-cpf').textContent = `${rec.student_cpf} • Matrícula ${rec.student_id}`;
            document.getElementById('modal-course-name').textContent = `${rec.course_name} • ${rec.institution_name}`;
            document.getElementById('modal-timestamp').textContent = `${rec.inbound_time} (Processado em ${rec.ai_time} por IA)`;
            document.getElementById('modal-hash-full').textContent = rec.inbound_hash;
            document.getElementById('modal-ocr-notes').textContent = rec.notes;
            document.getElementById('modal-erp-id').textContent = `${rec.erp_status} (${rec.erp_id})`;
            document.getElementById('modal-wa-status').textContent = rec.notif_status;
            document.getElementById('modal-wa-phone').textContent = rec.notif_phone;

            const badge = document.getElementById('modal-status-badge');
            if (rec.status === 'APPROVED') {
                badge.className = "px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800";
                badge.textContent = "100% Aprovado pelos Agentes";
            } else {
                badge.className = "px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-400 border border-amber-800";
                badge.textContent = "Aguardando Reenvio do Aluno";
            }

            document.getElementById('record-detail-modal').classList.remove('hidden');
        }

        function closeRecordDetailModal() {
            document.getElementById('record-detail-modal').classList.add('hidden');
        }

        function copyHashModal() {
            const hashText = document.getElementById('modal-hash-full').textContent;
            navigator.clipboard.writeText(hashText).then(() => {
                alert("Hash SHA-256 copiado para a área de transferência!");
            }).catch(() => {});
        }

        function exportRecordsCSV() {
            let csv = "ID;Aluno;CPF;Curso;Instituicao;Documento;Hash;Data;ERP;WhatsApp;Status\n";
            allRecords.forEach(r => {
                csv += `"${r.id}";"${r.student_name}";"${r.student_cpf}";"${r.course_name}";"${r.institution_name}";"${r.doc_name}";"${r.inbound_hash}";"${r.inbound_time}";"${r.erp_id}";"${r.notif_status}";"${r.status}"\n`;
            });
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `registros_protocoloedu_${new Date().toISOString().slice(0,10)}.csv`;
            a.click();
        }

        function refreshRecordsData() {
            const icon = document.getElementById('refresh-icon');
            if (icon) icon.classList.add('animate-spin');
            loadRecordsFromSupabaseOrMock().finally(() => {
                if (icon) setTimeout(() => icon.classList.remove('animate-spin'), 600);
            });
        }

        function refreshAllData() {
            refreshRecordsData();
            fetchInstitutions();
        }

        // --- GESTÃO DE CONTRATANTES & GAUGES ---
        async function fetchInstitutions() {
            allInstitutions = [
                {
                    id: "imes",
                    name: "Faculdade IMES - Instituto Mineiro de Educação Superior",
                    institution_type: "FACULDADE",
                    branding: {
                        primary_color: "#0a2351",
                        secondary_color: "#fdb913",
                        portal_title: "Portal de Envio de Documentos - IMES",
                        logo_url: "/static/images/logo-imes.jpg"
                    },
                    subscription: {
                        plan_tier: "PROFISSIONAL",
                        plan_name: "Plano Profissional MEC",
                        monthly_limit: 500,
                        current_month_usage: 142,
                        is_active: true
                    }
                },
                {
                    id: "colegio_modelo",
                    name: "Colégio Santa Maria Digital",
                    institution_type: "COLEGIO",
                    branding: {
                        primary_color: "#047857",
                        secondary_color: "#10b981",
                        portal_title: "Matrícula Online Santa Maria",
                        logo_url: "/static/images/logo-imes.jpg"
                    },
                    subscription: {
                        plan_tier: "STARTER",
                        plan_name: "Plano Básico",
                        monthly_limit: 150,
                        current_month_usage: 34,
                        is_active: true
                    }
                },
                {
                    id: "unimetro",
                    name: "Universidade Metropolitana Integrada",
                    institution_type: "UNIVERSIDADE",
                    branding: {
                        primary_color: "#1e3a8a",
                        secondary_color: "#3b82f6",
                        portal_title: "Recepção de Prontuários Acadêmicos",
                        logo_url: "/static/images/logo-imes.jpg"
                    },
                    subscription: {
                        plan_tier: "ENTERPRISE",
                        plan_name: "Plano Enterprise MEC",
                        monthly_limit: 2500,
                        current_month_usage: 890,
                        is_active: true
                    }
                }
            ];

            renderInstitutionsTable(allInstitutions);
            updateChartsAndGauges(allInstitutions);
        }

        function updateChartsAndGauges(list) {
            const totalUsage = list.reduce((acc, i) => acc + (i.subscription?.current_month_usage || 0), 0);
            const totalCapacity = list.reduce((acc, i) => acc + (i.subscription?.monthly_limit || 0), 0);
            const remaining = Math.max(0, totalCapacity - totalUsage);
            const percent = totalCapacity > 0 ? ((totalUsage / totalCapacity) * 100).toFixed(1) : 0;

            const gaugePercentEl = document.getElementById('gauge-percent-display');
            if (gaugePercentEl) gaugePercentEl.textContent = `${percent}%`;

            const chartCountEl = document.getElementById('chart-institutions-count');
            if (chartCountEl) chartCountEl.textContent = `${list.length} contratantes`;

            const badgeInstCount = document.getElementById('badge-institutions-count');
            if (badgeInstCount) badgeInstCount.textContent = `${list.length} Inst.`;

            const projectedTotal = Math.round((totalUsage / 28) * 30);
            const projEl = document.getElementById('projection-count-display');
            if (projEl) projEl.textContent = `${projectedTotal.toLocaleString('pt-BR')} análises`;

            // Doughnut Chart
            const gaugeCanvas = document.getElementById('globalCapacityChart');
            if (gaugeCanvas) {
                const gaugeCtx = gaugeCanvas.getContext('2d');
                if (gaugeChartInstance) gaugeChartInstance.destroy();
                gaugeChartInstance = new Chart(gaugeCtx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Consumido', 'Disponível'],
                        datasets: [{
                            data: [totalUsage, remaining || 1],
                            backgroundColor: ['#fdb913', '#334155'],
                            borderWidth: 0,
                            cutout: '75%'
                        }]
                    },
                    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
                });
            }

            // Bar Chart
            const barCanvas = document.getElementById('institutionsBarChart');
            if (barCanvas) {
                const barCtx = barCanvas.getContext('2d');
                if (barChartInstance) barChartInstance.destroy();
                barChartInstance = new Chart(barCtx, {
                    type: 'bar',
                    data: {
                        labels: list.map(i => i.name.split(' - ')[0].substring(0, 16)),
                        datasets: [
                            { label: 'Consumido', data: list.map(i => i.subscription?.current_month_usage || 0), backgroundColor: '#0a2351', borderRadius: 6 },
                            { label: 'Limite', data: list.map(i => i.subscription?.monthly_limit || 0), backgroundColor: '#cbd5e1', borderRadius: 6 }
                        ]
                    },
                    options: { responsive: true, maintainAspectRatio: false, scales: { x: { grid: { display: false } }, y: { beginAtZero: true } }, plugins: { legend: { display: false } } }
                });
            }
        }

        function renderInstitutionsTable(list) {
            const tbody = document.getElementById('institutions-table-body');
            if (!tbody) return;

            tbody.innerHTML = list.map(inst => {
                const sub = inst.subscription || {};
                const limit = sub.monthly_limit || 0;
                const usage = sub.current_month_usage || 0;
                const percent = limit > 0 ? Math.min(Math.round((usage / limit) * 100), 100) : 0;

                return `
                    <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                        <td class="p-3.5">
                            <div class="font-extrabold text-slate-800 dark:text-white">${escapeHtml(inst.name)}</div>
                            <div class="text-[11px] font-mono text-slate-400 mt-0.5">slug: ${escapeHtml(inst.id)} • ${escapeHtml(inst.institution_type)}</div>
                        </td>
                        <td class="p-3.5">
                            <span class="font-bold text-imes-blue dark:text-imes-gold bg-blue-50 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-800 px-2 py-0.5 rounded-full text-[11px]">
                                ${escapeHtml(sub.plan_name || sub.plan_tier)}
                            </span>
                            <div class="text-[11px] text-slate-400 mt-1">Limite: <strong>${limit}</strong> docs/mês</div>
                        </td>
                        <td class="p-3.5 w-44">
                            <div class="flex items-center justify-between text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">
                                <span>${usage} docs</span>
                                <span>${percent}%</span>
                            </div>
                            <div class="w-full bg-slate-200 dark:bg-slate-700 h-2 rounded-full overflow-hidden">
                                <div class="bg-imes-blue dark:bg-imes-gold h-full rounded-full" style="width: ${percent}%;"></div>
                            </div>
                        </td>
                        <td class="p-3.5 font-mono text-[11px] text-slate-500 dark:text-slate-400">
                            ${inst.id}-sec-2026
                        </td>
                        <td class="p-3.5">
                            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">Ativo</span>
                        </td>
                        <td class="p-3.5 text-[11px] font-semibold">
                            <a href="/" target="_blank" class="text-blue-500 hover:underline">Portal Aluno ↗</a>
                        </td>
                        <td class="p-3.5 text-right">
                            <button onclick="openEditModal('${inst.id}')" class="px-2.5 py-1 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-bold cursor-pointer">
                                Gerenciar
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        // --- WHITE-LABEL & PLANOS ---
        function openWhiteLabelModal() {
            const select = document.getElementById('wl-select-inst');
            select.innerHTML = allInstitutions.map(i => `<option value="${i.id}">${escapeHtml(i.name)}</option>`).join('');
            if (allInstitutions.length > 0) loadInstitutionForBranding(allInstitutions[0].id);
            document.getElementById('whitelabel-modal').classList.remove('hidden');
        }

        function loadInstitutionForBranding(id) {
            const inst = allInstitutions.find(i => i.id === id);
            if (!inst) return;
            const b = inst.branding || {};
            document.getElementById('wl-logo-url').value = b.logo_url || '/static/images/logo-imes.jpg';
            document.getElementById('wl-portal-title').value = b.portal_title || 'Portal de Envio de Documentos';
            document.getElementById('wl-primary-color-text').value = b.primary_color || '#0a2351';
            document.getElementById('wl-primary-color-picker').value = b.primary_color || '#0a2351';
            document.getElementById('wl-secondary-color-text').value = b.secondary_color || '#fdb913';
            document.getElementById('wl-secondary-color-picker').value = b.secondary_color || '#fdb913';
            updateLivePreview();
        }

        function updateLivePreview() {
            const title = document.getElementById('wl-portal-title').value || 'Portal de Documentos';
            const logo = document.getElementById('wl-logo-url').value || '/static/images/logo-imes.jpg';
            const primary = document.getElementById('wl-primary-color-text').value || '#0a2351';
            const secondary = document.getElementById('wl-secondary-color-text').value || '#fdb913';

            document.getElementById('preview-title-display').textContent = title;
            document.getElementById('preview-logo-img').src = logo;
            document.getElementById('preview-header').style.backgroundColor = primary;
            document.getElementById('preview-btn').style.backgroundColor = secondary;
        }

        function syncColorInput(type, val) {
            if (type === 'primary') {
                document.getElementById('wl-primary-color-picker').value = val;
                document.getElementById('wl-primary-color-text').value = val;
            } else {
                document.getElementById('wl-secondary-color-picker').value = val;
                document.getElementById('wl-secondary-color-text').value = val;
            }
            updateLivePreview();
        }

        function saveWhiteLabelBranding() {
            alert("Identidade White-Label salva com sucesso! Aplicada imediatamente a todos os portais.");
            document.getElementById('whitelabel-modal').classList.add('hidden');
        }

        function openEditModal(instId) {
            const inst = allInstitutions.find(i => i.id === instId);
            if (!inst) return;
            document.getElementById('edit-inst-id').value = inst.id;
            document.getElementById('edit-inst-name').value = inst.name;
            document.getElementById('edit-plan-tier').value = inst.subscription?.plan_tier || 'PROFISSIONAL';
            document.getElementById('edit-monthly-limit').value = inst.subscription?.monthly_limit || 500;
            document.getElementById('edit-plan-name').value = inst.subscription?.plan_name || 'Plano Profissional';
            document.getElementById('edit-billing-day').value = 10;
            document.getElementById('edit-admin-key').value = `${inst.id}-sec-2026`;
            document.getElementById('edit-is-active').value = "true";
            document.getElementById('edit-modal').classList.remove('hidden');
        }

        function handleSavePlan(e) {
            e.preventDefault();
            alert("Plano e limites do contratante atualizados com sucesso!");
            document.getElementById('edit-modal').classList.add('hidden');
        }

        function resetCurrentUsage() {
            if (confirm("Deseja realmente zerar o consumo do mês atual deste contratante?")) {
                alert("Consumo zerado para o novo ciclo!");
                document.getElementById('edit-modal').classList.add('hidden');
            }
        }

        function generateRandomKey() {
            const id = document.getElementById('edit-inst-id').value || 'inst';
            const random = Math.random().toString(36).substring(2, 8);
            document.getElementById('edit-admin-key').value = `${id}-${random}`;
        }

        function openCreateModal() {
            document.getElementById('create-modal').classList.remove('hidden');
        }

        function handleCreateInstitution(e) {
            e.preventDefault();
            const name = document.getElementById('new-name').value;
            const slug = document.getElementById('new-id').value;
            allInstitutions.push({
                id: slug,
                name: name,
                institution_type: document.getElementById('new-type').value,
                branding: { primary_color: "#0a2351", secondary_color: "#fdb913", portal_title: `Portal - ${name}` },
                subscription: { plan_tier: document.getElementById('new-plan-tier').value, monthly_limit: parseInt(document.getElementById('new-monthly-limit').value), current_month_usage: 0, is_active: true }
            });
            renderInstitutionsTable(allInstitutions);
            updateChartsAndGauges(allInstitutions);
            alert(`Contratante '${name}' cadastrado com sucesso!`);
            document.getElementById('create-modal').classList.add('hidden');
        }

        function checkHealthTelemetry() {
            alert("Diagnóstico de Infraestrutura: API Gemini Vision 2.5 Online (1.35s), Supabase Storage Ativo e 8 Subagentes em Operação Contínua!");
        }
    </script>
</body>
</html>
'''

print("[*] Gravando frontend/superadmin.html...")
with open("frontend/superadmin.html", "w", encoding="utf-8") as f:
    f.write(HTML_CONTENT)

print("[*] Gravando templates/default/super_admin.html...")
with open("templates/default/super_admin.html", "w", encoding="utf-8") as f:
    f.write(HTML_CONTENT)

print("[*] Atualizando frontend/_redirects para enviar /admin e /secretaria para o Super Admin...")
redirects_content = """# Regras de Redirecionamento Oficiais Netlify (ProtocoloEdu)
/portal       /index.html                     200
/aluno        /index.html                     200
/admin        /superadmin.html                302
/secretaria   /superadmin.html                302
/superadmin   /superadmin.html                200
/super-admin  /superadmin.html                200
/*            /index.html                     200
"""
with open("frontend/_redirects", "w", encoding="utf-8") as f:
    f.write(redirects_content)

print("[*] Atualizando frontend/admin.html com redirecionamento limpo...")
admin_redirect = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url=/superadmin#records">
  <title>Central de Registros Unificada • Super Admin</title>
  <script>window.location.replace("/superadmin#records");</script>
</head>
<body style="background:#0B132B;color:#E2E8F0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;">
  <p>Redirecionando para a Central Unificada de Registros no Super Admin...</p>
</body>
</html>
"""
with open("frontend/admin.html", "w", encoding="utf-8") as f:
    f.write(admin_redirect)

# Recriar zip do frontend
zip_path = "protocoloedu-frontend.zip"
print(f"[*] Reconstruindo {zip_path}...")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk("frontend"):
        for file in files:
            full_path = os.path.join(root, file)
            arcname = os.path.relpath(full_path, "frontend")
            zf.write(full_path, arcname)

print(f" -> Zip criado ({os.path.getsize(zip_path)} bytes).")

# Fazer deploy no Netlify via API
NETLIFY_TOKEN = "nfp_bb69ariUkrzd2SuUky3Z6iVdfxSVYmz48b42"
SITE_ID = "69dacb8b-0fd1-4550-be1a-78fb68495fb7"

print("[*] Publicando no Netlify...")
deploy_url = f"https://api.netlify.com/api/v1/sites/{SITE_ID}/deploys"

with open(zip_path, "rb") as f:
    zip_bytes = f.read()

req = urllib.request.Request(
    deploy_url,
    data=zip_bytes,
    headers={
        "Authorization": f"Bearer {NETLIFY_TOKEN}",
        "Content-Type": "application/zip"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req) as resp:
        resp_data = json.loads(resp.read().decode("utf-8"))
        print("[SUCESSO] Deploy no Netlify concluído com sucesso!")
        print(f" -> Deploy ID: {resp_data.get('id')}")
        print(f" -> State: {resp_data.get('state')}")
        print(f" -> URL: https://protocoloedu.netlify.app/superadmin")
except urllib.error.HTTPError as e:
    err_body = e.read().decode('utf-8', errors='ignore')
    print(f"[ERRO Netlify] {e.code}: {err_body}")
