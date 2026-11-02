# In�cio r�pido (portugu�s)

Copie `config.example.json` para `config.json` e configure o URL REST do seu blog e as fontes RSS de sua prefer�ncia. `config.json` � ignorado pelo Git. N�o salve senhas nos arquivos.

```powershell
python -m unittest discover -s tests -v
python -m openpublisher --config config.json collect
python -m openpublisher --config config.json generate
python -m openpublisher --config config.json publish
```

O �ltimo comando � simula��o sem acesso ao WordPress. Para publicar, configure as vari�veis de ambiente apropriadas, verifique o texto e as fontes, ajuste manualmente `reviewed` para `true` somente ap�s revis�o, e execute `python -m openpublisher publish --live --status draft`. Para uma postagem p�blica, escolha explicitamente `--status publish`.

Com WordPress.com usando API proxy, veja `config.wordpress-com.example.json` e configure `WP_CLIENT_ID`, `WP_CLIENT_SECRET`, `WP_USERNAME`, `WP_APP_PASSWORD` como segredos do seu ambiente. O uso de IA � opcional e pode gerar cobran�as de API independentes do ChatGPT Pro.

Leia `CODEX_GOAL.md` antes de pedir ao Codex para transformar este prot�tipo em produto est�vel para a comunidade.
