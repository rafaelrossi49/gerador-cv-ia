import os
from flask import Flask, request, jsonify, render_template_string
import requests
import pypdf
import docx

app = Flask(__name__)

# ==========================================
# TEMPLATE LATEX BASE (Raw String para manter barras)
# ==========================================
LATEX_TEMPLATE = r"""
\documentclass[10pt, a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[portuguese, english]{babel}
\usepackage[a4paper, top=1.2cm, bottom=1.2cm, left=1.5cm, right=1.5cm]{geometry}
\usepackage{helvet}
\renewcommand{\familydefault}{\sfdefault}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{hyperref}
\usepackage{xcolor}
\definecolor{darkblue}{RGB}{0,0,139}
\hypersetup{colorlinks=true, linkcolor=darkblue, urlcolor=darkblue}
\titleformat{\section}{\large\bfseries\uppercase}{}{0em}{}[\titlerule]
\titlespacing*{\section}{0pt}{8pt}{4pt}
\setlist[itemize]{label=\textbullet, leftmargin=1.5em, parsep=0pt, itemsep=2pt, topsep=2pt}
\setlength{\parindent}{0pt}
\pagestyle{empty}

\begin{document}

\begin{center}
    {\Large \textbf{NOME COMPLETO}} \\ \vspace{0.1cm}
    \textbf{Título Profissional Alvo (Ex: Engenheiro de Dados | Analista)} \\
    Cidade - UF | Telefone | Email \\
    \href{LINK_LINKEDIN}{LinkedIn}
\end{center}

\vspace{0.1cm}

\section{Resumo Profissional}
[Escreva aqui um resumo de 3-4 linhas, focado em vender o candidato para ESTA vaga específica, usando as palavras-chave da descrição.]

\section{Habilidades Técnicas}
\begin{itemize}
    \item \textbf{Categoria 1 (Ex: Linguagens):} Skill A, Skill B...
    \item \textbf{Categoria 2 (Ex: Ferramentas):} Skill C, Skill D...
    [Liste apenas o que é relevante para a vaga]
\end{itemize}

\section{Experiência Profissional}

\textbf{Empresa} \hfill Cidade - UF \\
\textit{Cargo} \hfill Mês/Ano -- Mês/Ano (ou Atual)
\begin{itemize}
    \item [Bullet point focado em resultado e na vaga. Use \textbf{negrito} para destacar tecnologias ou números.]
    \item [Bullet point focado em resolução de problemas.]
\end{itemize}

[Repetir para outras experiências relevantes]

\section{Educação}
\textbf{Instituição} \hfill Cidade - UF \\
Curso \hfill Previsão de Formatura: Mês/Ano

\section{Informações Adicionais}
\begin{itemize}
    \item [Idiomas, Projetos ou Cursos Extras que sejam diferenciais para a vaga]
\end{itemize}

\end{document}
"""

# ==========================================
# FRONTEND HTML + JS (Embutido)
# ==========================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gerador de Currículos ATS - IA</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100 text-gray-800 font-sans min-h-screen">
    <div class="max-w-5xl mx-auto py-10 px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-10">
            <h1 class="text-4xl font-extrabold text-blue-900 tracking-tight">Gerador de Currículos ATS</h1>
            <p class="mt-2 text-lg text-gray-600">Otimize seu currículo em LaTeX para qualquer vaga usando a API da OpenAI.</p>
        </div>

        <div class="bg-white shadow-xl rounded-lg overflow-hidden flex flex-col md:flex-row">
            <!-- Formulário Lateral Esquerdo -->
            <div class="md:w-1/2 p-6 bg-gray-50 border-r border-gray-200">
                <form id="cvForm" class="space-y-5">
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Perplexity API Key</label>
                        <input type="password" id="apiKey" required placeholder="pplx-..." 
                            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border">
                        <p class="text-xs text-gray-500 mt-1">Sua chave não é salva. Ela vai direto para a Perplexity.</p>
                    </div>

                    <div>
                        <label class="block text-sm font-medium text-gray-700">Descrição da Vaga</label>
                        <textarea id="jobDescription" rows="5" required placeholder="Cole a descrição da vaga aqui..."
                            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"></textarea>
                    </div>

                    <div>
                        <label class="block text-sm font-medium text-gray-700">Seu Currículo (Texto)</label>
                        <textarea id="resumeText" rows="4" placeholder="Cole seu currículo atual aqui..."
                            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"></textarea>
                    </div>

                    <div class="relative">
                        <div class="absolute inset-0 flex items-center" aria-hidden="true">
                            <div class="w-full border-t border-gray-300"></div>
                        </div>
                        <div class="relative flex justify-center">
                            <span class="px-2 bg-gray-50 text-sm text-gray-500">OU</span>
                        </div>
                    </div>

                    <div>
                        <label class="block text-sm font-medium text-gray-700">Seu Currículo (Arquivo PDF ou DOCX)</label>
                        <input type="file" id="resumeFile" accept=".pdf,.docx" 
                            class="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100">
                    </div>

                    <button type="submit" id="submitBtn" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors">
                        <i class="fas fa-magic mr-2 mt-0.5"></i> Gerar Currículo Otimizado
                    </button>
                </form>
            </div>

            <!-- Área de Resultado Lado Direito -->
            <div class="md:w-1/2 p-6 flex flex-col bg-gray-900 text-gray-100">
                <div class="flex justify-between items-center mb-2">
                    <h3 class="text-lg font-medium text-white">Código LaTeX Gerado</h3>
                    <button id="copyBtn" class="hidden text-sm bg-gray-700 hover:bg-gray-600 text-white py-1 px-3 rounded transition-colors">
                        <i class="fas fa-copy mr-1"></i> Copiar
                    </button>
                </div>
                
                <div id="loading" class="hidden flex-1 flex flex-col items-center justify-center">
                    <i class="fas fa-circle-notch fa-spin text-4xl text-blue-500 mb-4"></i>
                    <p class="text-gray-400">Analisando vaga e reescrevendo currículo...</p>
                </div>

                <div id="errorBox" class="hidden mt-4 bg-red-900/50 border border-red-500 text-red-200 p-4 rounded-md">
                </div>

                <textarea id="resultLatex" readonly class="w-full flex-1 bg-gray-800 border border-gray-700 rounded-md p-4 text-sm font-mono text-green-400 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none h-[500px]" placeholder="O código aparecerá aqui..."></textarea>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('cvForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitBtn = document.getElementById('submitBtn');
            const loading = document.getElementById('loading');
            const resultBox = document.getElementById('resultLatex');
            const copyBtn = document.getElementById('copyBtn');
            const errorBox = document.getElementById('errorBox');

            // Reset UI
            resultBox.value = '';
            errorBox.classList.add('hidden');
            copyBtn.classList.add('hidden');
            loading.classList.remove('hidden');
            submitBtn.disabled = true;
            submitBtn.classList.add('opacity-50', 'cursor-not-allowed');

            const formData = new FormData();
            formData.append('api_key', document.getElementById('apiKey').value);
            formData.append('job_description', document.getElementById('jobDescription').value);
            formData.append('resume_text', document.getElementById('resumeText').value);
            
            const fileInput = document.getElementById('resumeFile');
            if (fileInput.files.length > 0) {
                formData.append('resume_file', fileInput.files[0]);
            }

            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || 'Erro desconhecido na geração.');
                }

                resultBox.value = data.latex;
                copyBtn.classList.remove('hidden');

            } catch (error) {
                errorBox.textContent = error.message;
                errorBox.classList.remove('hidden');
            } finally {
                loading.classList.add('hidden');
                submitBtn.disabled = false;
                submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        });

        document.getElementById('copyBtn').addEventListener('click', () => {
            const resultBox = document.getElementById('resultLatex');
            resultBox.select();
            document.execCommand('copy');
            
            const btn = document.getElementById('copyBtn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check mr-1"></i> Copiado!';
            btn.classList.replace('bg-gray-700', 'bg-green-600');
            
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.classList.replace('bg-green-600', 'bg-gray-700');
            }, 2000);
        });
    </script>
</body>
</html>
"""

# ==========================================
# FUNÇÕES DE EXTRAÇÃO DE TEXTO
# ==========================================
def extract_text_from_pdf(file_stream):
    text = ""
    try:
        reader = pypdf.PdfReader(file_stream)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Erro ao ler PDF: {e}")
    return text

def extract_text_from_docx(file_stream):
    text = ""
    try:
        doc = docx.Document(file_stream)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"Erro ao ler DOCX: {e}")
    return text

# ==========================================
# ROTAS DO FLASK
# ==========================================
@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/generate', methods=['POST'])
def generate():
    api_key = request.form.get('api_key')
    job_description = request.form.get('job_description')
    resume_text_input = request.form.get('resume_text', '')
    resume_file = request.files.get('resume_file')

    if not api_key:
        return jsonify({"error": "A API Key da OpenAI é obrigatória."}), 400
    if not job_description:
        return jsonify({"error": "A descrição da vaga é obrigatória."}), 400

    # Determinar a origem do texto do currículo
    final_resume_text = resume_text_input

    if resume_file and resume_file.filename:
        filename = resume_file.filename.lower()
        if filename.endswith('.pdf'):
            extracted = extract_text_from_pdf(resume_file.stream)
            final_resume_text += f"\n{extracted}"
        elif filename.endswith('.docx'):
            extracted = extract_text_from_docx(resume_file.stream)
            final_resume_text += f"\n{extracted}"
        else:
            return jsonify({"error": "Formato de arquivo não suportado. Use PDF ou DOCX."}), 400

    if not final_resume_text.strip():
        return jsonify({"error": "Você precisa fornecer o texto do currículo ou fazer upload de um arquivo."}), 400

    # Configurar API da Perplexity via requests
    try:
        system_prompt = "Você é um Recrutador Técnico Sênior e Especialista em Engenharia de Currículos."
        user_prompt = f"""
Sua missão é reescrever o currículo do candidato transformando-o em um código LaTeX completo, 
otimizado especificamente para passar nos filtros de ATS e encantar o recrutador desta vaga.

REGRAS OBRIGATÓRIAS:
1. Altere o resumo e os bullet points para focar nas palavras-chave e requisitos da vaga.
2. Destaque resultados numéricos sempre que possível.
3. Se a vaga pedir inglês explícito, gere o currículo em inglês. Caso contrário, mantenha o idioma da vaga.
4. A saída DEVE SER APENAS O CÓDIGO LATEX. Não adicione markdown (```latex), não adicione explicações. Retorne o código puro.
5. Use EXATAMENTE o template LaTeX abaixo, preenchendo com os dados otimizados.

--- INICIO DO TEMPLATE LATEX ---
{LATEX_TEMPLATE}
--- FIM DO TEMPLATE ---

--- DADOS PARA PROCESSAMENTO ---

VAGA:
{job_description}

CURRÍCULO ATUAL:
{final_resume_text}
"""
        # Chamada direta via requests para garantir que vá para a Perplexity
        url = "https://api.perplexity.ai/chat/completions"
        payload = {
            "model": "sonar", 
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        api_response = requests.post(url, json=payload, headers=headers)

        if api_response.status_code != 200:
            return jsonify({"error": f"Erro na Perplexity: {api_response.text}"}), 500

        response_data = api_response.json()
        latex_output = response_data['choices'][0]['message']['content'].strip()

        # Limpar markdown indesejado caso a IA coloque
        if latex_output.startswith("```latex"):
            latex_output = latex_output.replace("```latex", "", 1)
        if latex_output.startswith("```"):
            latex_output = latex_output.replace("```", "", 1)
        if latex_output.endswith("```"):
            latex_output = latex_output[::-1].replace("```"[::-1], "", 1)[::-1]

        return jsonify({"latex": latex_output.strip()})

    except Exception as e:
        return jsonify({"error": f"Erro no processamento: {str(e)}"}), 500

if __name__ == '__main__':
    # Roda o servidor na porta 5000
    print("Servidor rodando! Acesse: [http://127.0.0.1:5000](http://127.0.0.1:5000)")
    app.run(debug=True, port=5000)