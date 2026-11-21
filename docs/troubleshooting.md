## Trouble shooting

If the Kleenex integration raises errors then first have a look at the Kleenex/Scottex website and check the pollen radar there:

- For France: https://www.kleenex.fr/alertes-pollens
- For Italy: https://www.it.scottex.com/allerta-pollini/previsioni-dei-pollini
- For Netherlands: https://www.kleenex.nl/pollenradar
- For UK and RoI: https://www.kleenex.co.uk/pollen-count
- For USA: https://www.kleenex.com/en-us/pollen-count

The Date sensor's `raw` attribute contains the response as text. Italian JSON
responses are serialized as JSON. The attribute is limited to 8192 characters,
so longer responses may be truncated.
