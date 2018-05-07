# inmodia

Telegram bot que envía al canal [@inmueblesparticularlp](https://t.me/inmueblesparticularlp) alquileres de inmuebles de La Plata tomados de los clasificados del Diario El Dia, filtrados por particular (opcional)

```bash
# editar env.prod.yml
$ cp env.{local,prod}.yml

# instalar serverless-python-requirements
$ npm install
```

Configurar [serverless](https://serverless.com/) con las credenciales de AWS y

```
$ serverless deploy -s prod
```