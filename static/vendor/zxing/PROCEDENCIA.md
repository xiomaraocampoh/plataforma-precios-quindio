# @zxing/library 0.21.3

- Origen: paquete npm `@zxing/library@0.21.3` (`npm pack`), archivo `umd/index.min.js`.
- Licencia: el archivo `LICENSE` del paquete es Apache 2.0 (el campo `license` de su package.json dice MIT); ambas son permisivas y se conserva el texto original.
- SHA-256 de `zxing-library.min.js`: `d7cc8f69dd70bdcf3ac00c9ae572bf2acb9f4132ba379c72df842e4db918652d`
- SHA-512 del tarball npm: `8591ea15ed89c87fd9c6f889668b198d5fb6b3a103498d0edb847e1509a55990595cff48a8ca3b4b79dbdfed8b056c687494244aeadd4069ea13b297aab620a3`
- Uso: decodificar códigos de barras en navegadores sin `BarcodeDetector` (Safari/iOS, Firefox).
  Se carga bajo demanda desde `static/js/escanear.js`; el decodificado ocurre en el navegador y la
  imagen no se envía al servidor.
- Para actualizar: repetir `npm pack`, reemplazar el archivo y actualizar este registro.
