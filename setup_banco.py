"""
Roda UMA VEZ para recriar tabelas e popular com receitas completas.
Execute: python setup_banco.py
"""
import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL não configurada.")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# ── Apaga e recria tabelas ────────────────────────────
cur.execute("DROP TABLE IF EXISTS historico CASCADE;")
cur.execute("DROP TABLE IF EXISTS ultima_receita CASCADE;")
cur.execute("DROP TABLE IF EXISTS cache CASCADE;")
cur.execute("DROP TABLE IF EXISTS receitas CASCADE;")

cur.execute("""
CREATE TABLE receitas (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    keywords TEXT[] NOT NULL,
    categoria TEXT NOT NULL,
    ingredientes TEXT,
    modo TEXT
);
""")

cur.execute("""
CREATE TABLE cache (
    chave TEXT PRIMARY KEY,
    resposta TEXT NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW()
);
""")

cur.execute("""
CREATE TABLE ultima_receita (
    session_id TEXT PRIMARY KEY,
    receita_id INTEGER REFERENCES receitas(id),
    atualizado_em TIMESTAMP DEFAULT NOW()
);
""")

cur.execute("""
CREATE TABLE historico (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    mensagem TEXT NOT NULL,
    resposta TEXT NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW()
);
""")

conn.commit()
print("Tabelas criadas.")

# ── Receitas ──────────────────────────────────────────
RECEITAS = [
    {
        "nome": "Sorvete Artesanal",
        "keywords": ["sorvete"],
        "categoria": "quente",
        "ingredientes": "1 litro de leite\n1 xicara de creme de leite\n1 e 1/2 xicara de acucar refinado\n1 xicara de leite em po\n1 colher (sopa) rasa de liga neutra\n1 colher (sopa) de po sabor para sorvete\n1 colher (sopa) de emulsificante",
        "modo": "1. Bater o leite, o creme de leite, o acucar, o leite em po e a liga neutra por 3 minutos no liquidificador.\n2. Colocar a mistura em vasilhas de aluminio para gelar.\n3. Depois de gelada, a mistura vira um bloco (massa basica do sorvete).\n4. Colocar a massa em pedacos na batedeira, juntar o sabor de sua preferencia e o emulsificante. Bater em velocidade maxima por 5 minutos.\n5. Colocar em potes fechados e levar ao freezer."
    },
    {
        "nome": "Mousse de Cafe com Chocolate",
        "keywords": ["mousse", "cafe"],
        "categoria": "quente",
        "ingredientes": "250ml de leite de coco\n12g de gelatina sem sabor\n100ml de cafe\n2 colheres (sopa) de adocante\nEssencia de baunilha a gosto\nCobertura:\n150ml de leite de coco\n50ml de cafe\n2 colheres (sopa) de adocante\n1 colher (sopa) de cacau sem acucar",
        "modo": "1. Hidratar a gelatina no cafe, mexer ate dissolver bem (reserve).\n2. No liquidificador acrescente o leite de coco, essencia de baunilha, o adocante e por ultimo a gelatina dissolvida no cafe. Bater por 1 minuto.\n3. Despeje em um refratario e leve a geladeira por 2 horas.\n4. Para a cobertura: misture todos os ingredientes e leve ao micro-ondas de 30 em 30 segundos ate formar uma calda. Deixe esfriar.\n5. Espalhe a cobertura sobre a mousse gelada e leve a geladeira por mais 30 minutos."
    },
    {
        "nome": "Mousse de Morango sem Leite Condensado",
        "keywords": ["morango"],
        "categoria": "quente",
        "ingredientes": "1 caixinha de morangos picados\n1 caixinha de creme de leite\n2 potes de iogurte natural",
        "modo": "1. Bata no liquidificador todos os ingredientes.\n2. Despeje em tacas individuais.\n3. Leve a geladeira por 3 horas.\n4. Decore com pedacos de morango na hora de servir."
    },
    {
        "nome": "Bombom de Prestigio",
        "keywords": ["prestigio"],
        "categoria": "quente",
        "ingredientes": "1/2 lata de leite condensado (200g)\n2 pacotes de coco ralado (200g)\n200g de chocolate ao leite ou meio amargo",
        "modo": "1. Misture bem o coco ralado com o leite condensado.\n2. Faca bolinhas e disponha em uma forma.\n3. Leve a geladeira por 30 minutos.\n4. Derreta o chocolate e banhe os bombons.\n5. Coloque sobre papel manteiga e deixe secar."
    },
    {
        "nome": "Bombom Surpresa com Pacoca",
        "keywords": ["pacoca", "surpresa"],
        "categoria": "quente",
        "ingredientes": "200g de bolacha maisena moida\n1 xicara de pacoca picada (aprox. 7 pacocas)\n1 lata de leite condensado\nUvas verdes sem sementes\n300g de chocolate meio amargo fracionado",
        "modo": "1. Misture a bolacha moida com a pacoca e va acrescentando o leite condensado aos poucos ate chegar ao ponto de brigadeiro.\n2. Umedeca a palma da mao com agua, pegue um pouco da mistura e faca bolinhas.\n3. Aperte cada bolinha na palma da mao, coloque uma uva no meio e feche.\n4. Derreta o chocolate fracionado e banhe as bolinhas.\n5. Coloque sobre papel manteiga e deixe secar."
    },
    {
        "nome": "Bicho de Pe",
        "keywords": ["bicho de pe"],
        "categoria": "quente",
        "ingredientes": "1 lata de leite condensado\n1 pacote de gelatina de morango\n1 colher (sopa) de manteiga ou margarina sem sal\nAcucar cristal para passar",
        "modo": "1. Em uma panela de fundo grosso, misture o leite condensado, a manteiga e a gelatina.\n2. Leve ao fogo baixo mexendo sem parar ate desgrudar do fundo (ponto de brigadeiro).\n3. Despeje em um recipiente, cubra com plastico filme e leve a geladeira para esfriar.\n4. Apos esfriar, passe um pouco de oleo nas maos e enrole os docinhos.\n5. Passe no acucar cristal e sirva."
    },
    {
        "nome": "Pacoquinha de Leite Condensado",
        "keywords": ["pacoquinha", "amendoim"],
        "categoria": "quente",
        "ingredientes": "250g de amendoim torrado e moido\n1/2 pacote de bolacha maisena moida (100g aprox.)\n1/2 lata de leite condensado",
        "modo": "1. Misture com a mao amassando bem todos os ingredientes ate virar uma massa compacta.\n2. Distribua a massa em uma assadeira untada, apertando bem.\n3. Leve a geladeira por 30 minutos.\n4. Apos endurecer, corte no tamanho desejado."
    },
    {
        "nome": "Pizza de Chocolate Brigadeiro",
        "keywords": ["pizza"],
        "categoria": "quente",
        "ingredientes": "1 disco de pizza medio (assado)\n1 lata de leite condensado\n1 colher (sopa) de cacau em po\n1 colher (sobremesa) de chocolate em po\nGranulado, cerejas em calda e folhas de hortela a gosto",
        "modo": "1. Misture o leite condensado, o cacau e o chocolate em po numa panela.\n2. Leve ao fogo mexendo ate comecar a desgrudar do fundo (ponto de brigadeiro).\n3. Espalhe o brigadeiro sobre a massa ja assada.\n4. Finalize com granulado, cerejas e folhas de hortela."
    },
    {
        "nome": "Petit Gateau de Bacuri",
        "keywords": ["petit", "gateau", "bacuri"],
        "categoria": "quente",
        "ingredientes": "200g de chocolate branco\n250g de manteiga\n5 gemas\n5 ovos inteiros\n350g de polpa de bacuri\n40g de acucar refinado",
        "modo": "1. Derreta a manteiga e o chocolate branco em banho-maria.\n2. Retire do fogo e acrescente os ovos, as gemas e o acucar, mexendo com fouet.\n3. Ainda morno, acrescente a polpa de bacuri e misture.\n4. Unte as forminhas com manteiga e chocolate em po.\n5. Pre-aqueca o forno a 180 graus C e asse de 6 a 10 minutos (o centro deve ficar cremoso)."
    },
    {
        "nome": "Sequilhos de Limao",
        "keywords": ["sequilho", "limao"],
        "categoria": "quente",
        "ingredientes": "250g de amido de milho\n80g de acucar\n50g de manteiga\nRaspas e suco de 1 limao",
        "modo": "1. Em um recipiente, acrescente o amido, o acucar, a manteiga e as raspas de limao. Misture ate formar uma farofa.\n2. Adicione o suco de limao aos poucos ate dar ponto para enrolar.\n3. Faca rolinhos e corte os sequilhos no tamanho desejado.\n4. Coloque em assadeira e leve a geladeira por 5 a 10 minutos.\n5. Leve ao forno pre-aquecido a 160 graus C de 15 a 18 minutos."
    },
    {
        "nome": "Bolo de Abacaxi com Doce de Leite",
        "keywords": ["abacaxi", "doce de leite"],
        "categoria": "frio",
        "ingredientes": "Massa:\n1 ovo inteiro\n1 xicara de acucar\n50g de manteiga sem sal\n1 copo de iogurte\n4 colheres (sopa) de coco ralado desidratado\n1 pitada de sal\n1 xicara de farinha de trigo\n1 colher (sopa) rasa de fermento em po\nMontagem:\n1 abacaxi pequeno cortado em cubos\n1 lata de doce de leite",
        "modo": "1. Misture os cubos de abacaxi com o doce de leite e reserve.\n2. Bata o ovo com o acucar ate ficar uma mistura clara.\n3. Junte a manteiga e o iogurte. Acrescente o coco ralado, o sal e a mistura de ovos.\n4. Acrescente a farinha misturando delicadamente. Por ultimo, acrescente o fermento.\n5. Em uma assadeira, coloque uma camada de massa, o recheio de abacaxi e cubra com o restante da massa.\n6. Polvilhe coco ralado e leve ao forno pre-aquecido a 180 graus C por 30 minutos."
    },
    {
        "nome": "Bolo de Cenoura com Pudim de Chocolate",
        "keywords": ["cenoura"],
        "categoria": "frio",
        "ingredientes": "Bolo:\n2 ovos\n1 cenoura media\n1/2 xicara de oleo\n1 xicara de acucar\n1 xicara de farinha de trigo\n1 e 1/2 colher (cha) de fermento\nPudim:\n1 xicara de acucar (para caramelizar)\n1 lata de leite condensado\nA mesma medida de leite\n3 ovos\n5 colheres de chocolate em po",
        "modo": "1. Em uma forma para pudim, caramelize o acucar no fogo ate dourar.\n2. No liquidificador, bata todos os ingredientes do pudim e despeje na forma caramelizada.\n3. Bata no liquidificador a cenoura, os ovos e o oleo. Transfira para um recipiente e acrescente a farinha, o acucar e por ultimo o fermento.\n4. Despeje a mistura do bolo sobre o pudim.\n5. Leve ao forno pre-aquecido a 180 graus C por aproximadamente 1 hora."
    },
    {
        "nome": "Bolo de Couve",
        "keywords": ["couve"],
        "categoria": "frio",
        "ingredientes": "3 folhas medias de couve lavadas e picadas\n3 ovos inteiros\n250g de acucar\n60ml de oleo\n250g de farinha de trigo\n1 colher (sopa) de fermento quimico\n200ml de suco de laranja",
        "modo": "1. No liquidificador, bata a couve, os ovos, o acucar e o oleo.\n2. Transfira para uma travessa e acrescente a farinha, o fermento e aos poucos o suco de laranja.\n3. Despeje em forma untada.\n4. Leve ao forno pre-aquecido a 180 graus C de 35 a 40 minutos."
    },
    {
        "nome": "Bolo de Fuba",
        "keywords": ["fuba"],
        "categoria": "frio",
        "ingredientes": "3 ovos\n2 xicaras de acucar\n2 xicaras de fuba\n1 xicara de farinha de trigo\n1 xicara de oleo\n1 xicara de leite\n1 colher (sopa) de fermento em po",
        "modo": "1. Bata o acucar com os ovos ate formar um creme claro.\n2. Acrescente aos poucos os demais ingredientes, menos o fermento.\n3. Apos bater bem, acrescente o fermento e misture delicadamente.\n4. Unte uma assadeira com manteiga e acucar cristal.\n5. Leve ao forno pre-aquecido a 180 graus C por 40 minutos ou ate dourar."
    },
    {
        "nome": "Bolo de Mandioca Cremoso",
        "keywords": ["mandioca"],
        "categoria": "frio",
        "ingredientes": "500g de mandioca crua ralada\n200ml de leite de coco\n1 colher (sopa) de manteiga\n2 ovos\n1/2 xicara de coco ralado seco\n1 xicara de acucar",
        "modo": "1. Misture bem todos os ingredientes.\n2. Unte a forma com oleo e acucar.\n3. Leve ao forno pre-aquecido a 180 graus C por 40 a 50 minutos."
    },
    {
        "nome": "Bolo de Chocolate Peteleco",
        "keywords": ["peteleco", "chocolate"],
        "categoria": "frio",
        "ingredientes": "Massa:\n3 xicaras de farinha de trigo\n2 xicaras de acucar\n1 xicara de chocolate em po\n1 colher (cha) de fermento em po\n1 colher (cha) de bicarbonato de sodio\n1 xicara de oleo\n2 ovos\n2 xicaras de agua fervente\nCobertura:\n6 colheres (sopa) de acucar\n2 colheres (sopa) de chocolate em po\n1 colher (cha) de raspas de laranja\n1 colher (cha) de manteiga\n1/2 xicara de agua",
        "modo": "1. Peneire a farinha, o acucar, o chocolate, o fermento e o bicarbonato.\n2. Junte o oleo, os ovos e a agua fervente, misturando bem.\n3. Despeje em assadeira retangular untada.\n4. Asse em forno medio-alto (200 graus C) por 25 minutos.\n5. Para a cobertura: misture todos os ingredientes e leve ao fogo baixo ate obter calda grossa.\n6. Espalhe sobre o bolo ainda quente."
    },
    {
        "nome": "Bolo de Macaxeira Caramelizado",
        "keywords": ["macaxeira"],
        "categoria": "frio",
        "ingredientes": "1 kg de macaxeira ralada\n4 ovos\n2 xicaras de acucar\n1 xicara de leite\n1 vidro de leite de coco\n1 xicara de farinha de trigo\n1 colher (sopa) de fermento quimico\n1/2 colher (cha) de sal\n1 xicara de coco ralado",
        "modo": "1. Coloque a macaxeira ralada em uma tigela.\n2. Bata no liquidificador os ovos, o acucar, o leite de coco, o sal e o leite.\n3. Despeje na tigela com a macaxeira. Misture bem e acrescente o coco ralado, a farinha e por ultimo o fermento.\n4. Coloque em forma caramelizada.\n5. Leve ao forno pre-aquecido a 220 graus C por 50 a 60 minutos."
    },
    {
        "nome": "Pastel de Forno com Creme de Galinha",
        "keywords": ["pastel", "galinha", "guarana"],
        "categoria": "frio",
        "ingredientes": "Massa:\n1 lata de refrigerante guarana\n500g de farinha de trigo\n300g de manteiga amolecida\nSal a gosto\n1 gema de ovo para pincelar\nRecheio:\n500g de peito de frango cozido e desfiado\n1 cebola picada\n2 colheres (sopa) de azeite\n2 colheres (sopa) de farinha de trigo\n1 xicara de leite\nSal, pimenta e salsinha a gosto",
        "modo": "1. Misture todos os ingredientes da massa e amasse ate desgrudar das maos. Deixe descansar 30 minutos.\n2. Refogue a cebola no azeite. Junte o frango e a farinha. Adicione o leite aos poucos ate engrossar. Acerte o tempero.\n3. Ligue o forno a 180 graus C. Abra a massa, corte discos, coloque o recheio e feche. Pincele com a gema.\n4. Leve ao forno a 200 graus C por 20 minutos ou ate dourar."
    },
    {
        "nome": "Pudim de Queijo",
        "keywords": ["pudim"],
        "categoria": "frio",
        "ingredientes": "Calda:\n1 e 1/2 xicara de acucar cristal\n1/2 xicara de agua\nPudim:\n2 latas de leite condensado\n2 copos de iogurte natural\n5 ovos\n1/2 xicara de farinha de trigo\n200g de queijo coalho ralado\n1 colher (cafe) de fermento",
        "modo": "1. Para a calda: misture o acucar e a agua e deixe ferver ate caramelizar. Caramelize a forma.\n2. Bata no liquidificador o iogurte, o leite condensado, os ovos e o queijo.\n3. Junte a farinha e o fermento e bata novamente.\n4. Coloque na forma caramelizada e leve ao forno em banho-maria por 40 minutos a 180 graus C."
    },
    {
        "nome": "Navete Francesa",
        "keywords": ["navete"],
        "categoria": "frio",
        "ingredientes": "Massa:\n250g de margarina\n250g de farinha de trigo\n3 gemas\n30ml de agua\nRecheio:\n600g de presunto\n200g de queijo mussarela\n200g de ricota\n50g de uvas passas\n50g de azeitona\n200g de milho verde\n3 ovos\n20g de cheiro verde\n400g de creme de leite",
        "modo": "1. Para o recheio: processe o presunto e o queijo. Misture com o restante dos ingredientes.\n2. Para a massa: junte a margarina, o trigo, as gemas e a agua. Amasse ate ficar macia.\n3. Coloque a massa nas forminhas, acrescente o recheio.\n4. Leve ao forno medio a 180 graus C por 20 a 30 minutos."
    },
    {
        "nome": "Pao de Mel",
        "keywords": ["pao de mel"],
        "categoria": "frio",
        "ingredientes": "3 xicaras de farinha de trigo\n1 xicara de acucar\n1/2 xicara de chocolate em po\n1 colher (sobremesa) de bicarbonato\n1 colher (cafe) de cravo em po\n1 colher (cafe) de canela em po\n1 e 1/2 xicara de leite morno\n1/2 xicara de mel",
        "modo": "1. Coloque todos os ingredientes secos peneirados em uma vasilha.\n2. Acrescente o mel e o leite morno. Misture com a mao.\n3. Unte as forminhas de pao de mel.\n4. Leve ao forno pre-aquecido a 200 graus C por 20 minutos. Deixe esfriar e desenforme.\n5. Recheie com brigadeiro, beijinho ou doce de leite.\n6. Derreta chocolate ao leite e banhe os paes de mel."
    },
    {
        "nome": "Joelho ou Enroladinho de Presunto e Queijo",
        "keywords": ["presunto", "joelho"],
        "categoria": "frio",
        "ingredientes": "500ml de agua morna\n150ml de oleo\n4 colheres (sopa) de acucar\n1 colher (sopa) de sal\n2 pacotes de fermento biologico seco (20g)\n1kg de farinha de trigo\n500g de presunto\n500g de mussarela\nMolho de tomate e oregano a gosto",
        "modo": "1. Misture a agua morna, o oleo, acucar, sal e o fermento. Adicione a farinha aos poucos e sove por 10 minutos.\n2. Deixe descansar por 10 minutos.\n3. Abra a massa, recheie com presunto, molho e queijo, feche e corte.\n4. Passe gema e polvilhe oregano.\n5. Leve ao forno pre-aquecido a 220 graus C por 30 a 35 minutos."
    },
    {
        "nome": "Pao de Queijo Simples",
        "keywords": ["pao de queijo"],
        "categoria": "basico",
        "ingredientes": "1/2 xicara de parmesao ralado\n1/2 xicara de polvilho azedo ou doce\n1/2 caixinha de creme de leite\nSal a gosto",
        "modo": "1. Misture o parmesao e o polvilho.\n2. Va acrescentando o creme de leite aos poucos ate obter uma massa que de para fazer bolinhas.\n3. Faca as bolinhas e coloque em assadeira untada.\n4. Leve ao forno pre-aquecido a 180 graus C ate dourar."
    },
    {
        "nome": "Pao de Sal ou Pao de Leite",
        "keywords": ["pao de sal", "pao de leite"],
        "categoria": "basico",
        "ingredientes": "2 envelopes de fermento biologico seco (20g)\n1 copo de leite (250ml)\n1/3 xicara de acucar\n1/3 xicara de leite em po\n2 ovos\n2 colheres (sopa) de manteiga\n1/2 colher (sopa) de sal\n600g de farinha de trigo\n1 gema + 2 colheres de leite para pincelar",
        "modo": "1. Misture o fermento, o leite, o acucar, o leite em po, os ovos e o sal.\n2. Va acrescentando a farinha aos poucos e sove por 10 minutos.\n3. Divida em porcoes, boleie e deixe descansar ate dobrar de volume.\n4. Abra cada porcao com rolo e enrole para formar os paes.\n5. Coloque em assadeira untada e deixe descansar por mais 30 minutos.\n6. Pincele com a gema e leve ao forno a 180 graus C por 25 minutos."
    },
    {
        "nome": "Pao Caseiro Recheado",
        "keywords": ["pao caseiro"],
        "categoria": "basico",
        "ingredientes": "1 kg de farinha de trigo\n100g de acucar\n20g de sal\n50g de leite em po\n70g de margarina\n2 ovos\n200ml de leite\n15 a 20g de fermento biologico\nAgua gelada para dar o ponto\nRecheio de sua preferencia",
        "modo": "1. Misture todos os ingredientes secos. Adicione os ovos e o leite. De o ponto com agua gelada. Sove ate a massa ficar macia.\n2. Divida em pedacos de 200 a 250g. Abra com rolo e acrescente o recheio.\n3. Enrole como rocambole e disponha em assadeira untada.\n4. Asse em forno medio a 180 graus C por 30 a 40 minutos."
    },
    {
        "nome": "Mini Focaccia",
        "keywords": ["focaccia"],
        "categoria": "basico",
        "ingredientes": "1 kg de farinha de trigo\n20g de sal\n200g de acucar\n100g de margarina\n2 ovos\n30g de fermento biologico\n500ml de leite\nAzeite de oliva para untar",
        "modo": "1. Misture o fermento com o acucar ate dissolver. Acrescente o leite, a margarina e os ovos.\n2. Adicione a farinha e o sal aos poucos. Sove bem.\n3. Forme uma bola, cubra e deixe descansar ate dobrar de volume.\n4. Abra a massa em forma untada com azeite. Pressione com as pontas dos dedos.\n5. Regue com azeite e acrescente o recheio desejado. Deixe descansar 20 minutos.\n6. Leve ao forno a 200 graus C por 20 minutos."
    },
    {
        "nome": "Enroladinho de Salsicha",
        "keywords": ["salsicha", "enroladinho"],
        "categoria": "basico",
        "ingredientes": "250ml de agua morna\n75ml de oleo\n2 colheres (sopa) de acucar\n1/2 colher (sopa) de sal\n1 pacote de fermento biologico seco (10g)\n500g de farinha de trigo\n2 salsichas cortadas em 3 partes cada",
        "modo": "1. Misture todos os ingredientes da massa e sove ate dar ponto.\n2. Faca bolinhas de 10g cada.\n3. Abra cada bolinha, coloque um pedaco de salsicha com molho e enrole.\n4. Disponha em assadeira untada.\n5. Leve ao forno pre-aquecido a 180 graus C ate dourar."
    },
    {
        "nome": "Cookies de Chocolate",
        "keywords": ["cookie"],
        "categoria": "basico",
        "ingredientes": "1 kg de pre-mistura para cookie\n200g de farinha de trigo\n300g de margarina\n6 ovos\n200g de gotas de chocolate",
        "modo": "1. Coloque todos os ingredientes na batedeira e bata por 2 minutos.\n2. Acrescente as gotas de chocolate.\n3. Transfira para formas untadas.\n4. Asse por 35 a 40 minutos a 180 graus C."
    },
    {
        "nome": "Baguete Recheada",
        "keywords": ["baguete"],
        "categoria": "basico",
        "ingredientes": "500ml de agua temperatura ambiente\n50ml de azeite\n1 colher (sopa) de acucar\n1 colher (sopa) rasa de sal\n2 colheres (sopa) de fermento seco\n800g de farinha de trigo\n300g de presunto\n200g de queijo mussarela",
        "modo": "1. Misture a agua, o azeite, o acucar, o sal e o fermento. Va acrescentando a farinha e sove por 10 minutos.\n2. Deixe descansar por 10 minutos.\n3. Abra a massa bem fina, coloque o recheio e feche as pontas.\n4. Faca cortes em diagonal e pincele a gema.\n5. Deixe descansar de 10 a 15 minutos.\n6. Leve ao forno a 180 graus C por 18 a 20 minutos."
    },
    {
        "nome": "Bolinho de Queijo",
        "keywords": ["bolinho"],
        "categoria": "basico",
        "ingredientes": "100g de queijo mussarela ralado grosso\n100g de queijo prato ralado grosso\n1/4 colher (cha) de sal\n1/2 colher (cha) de oregano\n1/8 colher (cha) de pimenta do reino\n1 e 1/2 colher (sopa) de claras\n1/4 xicara de amido de milho",
        "modo": "1. Em uma tigela, acrescente todos os ingredientes e misture bem.\n2. Faca bolinhas pequenas de 10g cada.\n3. Passe no amido de milho.\n4. Frite em oleo quente a 180 graus C."
    },
    {
        "nome": "Pao de Aveia com Iogurte",
        "keywords": ["aveia"],
        "categoria": "basico",
        "ingredientes": "4 ovos\n1 pote de iogurte natural (170g)\nSal a gosto\n50g de queijo parmesao ralado\n2 xicaras de farinha de aveia\n1 colher (sobremesa) fermento quimico",
        "modo": "1. No liquidificador coloque todos os ingredientes, menos o fermento.\n2. Acrescente o fermento e misture com espatula.\n3. Despeje em forma de silicone untada e enfarinhada.\n4. Polvilhe queijo parmesao.\n5. Leve ao forno a 180 graus C entre 20 a 25 minutos."
    },
    {
        "nome": "Pao de Milho",
        "keywords": ["milho"],
        "categoria": "basico",
        "ingredientes": "75ml de leite\n1/2 lata de milho em conserva (sem agua)\n1 ovo\n1/2 colher (sopa) de essencia de baunilha\n1 e 1/2 colher (sopa) de manteiga\n1/4 colher (sopa) de sal\n1/2 lata de leite condensado\n10g de fermento biologico seco\n500g de farinha de trigo",
        "modo": "1. No liquidificador, bata o leite e o milho.\n2. Acrescente o ovo, a baunilha, a manteiga, o sal, o leite condensado e bata. Por ultimo acrescente o fermento.\n3. Despeje em uma tigela, va acrescentando a farinha e sovando por 10 minutos.\n4. Deixe descansar por 30 minutos.\n5. Divida em 10 partes, boleie e deixe descansar por mais 1 hora.\n6. Pincele uma gema e leve ao forno a 180 graus C por 35 minutos."
    },
    {
        "nome": "Pao de Cenoura",
        "keywords": ["pao de cenoura"],
        "categoria": "basico",
        "ingredientes": "1/3 de xicara de oleo\n1 colher (sopa) de manteiga\n2 xicaras de cenoura\n1 ovo\n2 colheres (sopa) de acucar\n7g de fermento biologico seco\n500g de farinha de trigo",
        "modo": "1. Bata todos os ingredientes no liquidificador exceto o fermento e a farinha.\n2. Transfira para um recipiente, acrescente o fermento e misture.\n3. Acrescente a farinha aos poucos ate dar o ponto.\n4. Cubra e deixe descansar por 1 hora.\n5. Modele os paezinhos e leve ao forno a 200 graus C por 20 minutos."
    },
    {
        "nome": "Pao de Abacate",
        "keywords": ["abacate"],
        "categoria": "basico",
        "ingredientes": "1 abacate medio maduro (400g de polpa)\n100ml de oleo\n250ml de leite\n2 ovos\n1/2 xicara de acucar\n1 pacote de fermento biologico seco\n1kg de farinha de trigo\n1 colher (cha) de sal",
        "modo": "1. No liquidificador, bata o abacate, o oleo, o leite, os ovos e o acucar. Acrescente o fermento e bata mais um pouco.\n2. Despeje em uma tigela, acrescente o sal e aos poucos a farinha ate a massa comecar a desgrudar da mao.\n3. Sove por 10 minutos.\n4. Deixe descansar por 30 minutos.\n5. Abra a massa, enrole como rocambole e deixe descansar por mais 30 minutos.\n6. Leve ao forno a 180 graus C por 30 minutos."
    },
    {
        "nome": "Torta de Escarola",
        "keywords": ["escarola", "torta"],
        "categoria": "basico",
        "ingredientes": "Massa:\n500g de farinha de trigo\n1/2 copo de agua\n1/2 copo de oleo\n1 colher (sopa) de vinagre\nSal a gosto\nRecheio:\n1 maco de escarola\n2 dentes de alho\n1 cebola media\nAzeite, sal e temperos a gosto\n2 tomates medios em fatias\n150g de mussarela\nOregano a gosto",
        "modo": "1. Corte a escarola bem fina. Refogue no azeite com a cebola e alho ate soltar agua. Tempere e reserve.\n2. Misture a agua, o oleo e va acrescentando farinha ate dar um ponto.\n3. Divida a massa em duas partes e abra bem fina.\n4. Forre a forma com uma parte. Coloque o recheio, o tomate e oregano.\n5. Finalize com mussarela e feche com a outra parte da massa.\n6. Leve ao forno a 180 graus C por 1 hora ate dourar."
    },
    {
        "nome": "Pamonha de Forno",
        "keywords": ["pamonha"],
        "categoria": "basico",
        "ingredientes": "3 latas de milho verde\n4 ovos\n1 vidro de leite de coco (200ml)\n1 lata de leite condensado (395ml)\n1 colher (sopa) de manteiga sem sal\n1 xicara de leite (210ml)\n1 colher (sopa) de fermento quimico",
        "modo": "1. Bata no liquidificador o milho, os ovos e o leite de coco por 3 minutos.\n2. Acrescente o leite condensado, o leite e a manteiga e bata por mais 4 minutos.\n3. Por ultimo acrescente o fermento e bata um pouco.\n4. Despeje em forma untada com manteiga e farinha de milho.\n5. Leve ao forno a 180 graus C por 1 hora."
    },
    {
        "nome": "Empadinha de Leite Condensado",
        "keywords": ["empadinha"],
        "categoria": "basico",
        "ingredientes": "1/2 xicara de farinha de trigo (70g)\n3 e 1/2 colher de manteiga em ponto de pomada (38g)\n200ml de leite condensado",
        "modo": "1. Misture a farinha e a manteiga ate formar uma massa lisa.\n2. Abra a massa em forminhas de empadas e leve a geladeira por 20 minutos.\n3. Pre-aqueca o forno a 180 graus C.\n4. Preencha metade de cada forminha com leite condensado.\n5. Leve ao forno a 180 graus C por 20 a 25 minutos ou ate o leite condensado comecar a dourar.\n6. Deixe esfriar para desenformar."
    },
    {
        "nome": "Eclair",
        "keywords": ["eclair", "carolina"],
        "categoria": "basico",
        "ingredientes": "Massa:\n80g de farinha de trigo\n2 ovos\n70g de manteiga sem sal\n140ml de agua\n3g de acucar\nRecheio (Creme de Baunilha):\n2 ovos\n240ml de leite\n60g de acucar\n20g de amido de milho\n20g de manteiga sem sal\nEssencia de baunilha a gosto\nCobertura (Ganache):\n50g de creme fresco\n50g de chocolate amargo",
        "modo": "1. Em uma panela acrescente a manteiga, acucar, sal e a agua e leve ao fogo ate a manteiga derreter. Desligue, acrescente a farinha mexendo bem. Cozinhe por mais 2 minutos.\n2. Despeje em uma tigela, espalhe e deixe esfriar. Acrescente os ovos batidos aos poucos ate a massa desgrudar da espatula formando um V.\n3. Coloque em saco de confeitar e faca canudinhos de 10cm em forma com papel manteiga.\n4. Leve ao forno a 180 graus C por 25 minutos. Baixe para 160 graus C por mais 15 minutos. Retire e deixe esfriar.\n5. Para o recheio: misture os ovos, o acucar, o amido e o leite numa panela. Leve ao fogo mexendo ate borbulhar. Retire, acrescente a manteiga, cubra com plastico filme e leve a geladeira.\n6. Para o ganache: derreta o chocolate em banho maria e acrescente o creme de leite.\n7. Recheie os eclairs com o creme e cubra com o ganache."
    },
]

for r in RECEITAS:
    cur.execute("""
        INSERT INTO receitas (nome, keywords, categoria, ingredientes, modo)
        VALUES (%s, %s, %s, %s, %s)
    """, (r["nome"], r["keywords"], r["categoria"], r["ingredientes"], r["modo"]))

conn.commit()
cur.execute("SELECT COUNT(*) FROM receitas;")
print(f"Receitas inseridas: {cur.fetchone()[0]}")

cur.close()
conn.close()
print("Pronto!")