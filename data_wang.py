#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Richard 'Data' Wang

Programita para parsear los ficheros `.txt` exportados por la Lenzing del
laboratorio para construir una hoja de cálculo con los valores de la fibra
por lote y día.
"""

from collections import defaultdict
import os
import csv
import datetime
import argparse


def check_fila3(fila):
    """A causa de algunos retornos de carro en la cadena que guarda el lote
    en los ficheros fuentes, a veces la fila 3 es la continuación del lote
    de la fila 2. Esta función comprueba si es así buscando unos textos fijos
    que siempre están presentes únicamente en la fila 3.
    """
    return "Titer" in fila and "Force" in fila


def any_number(cad):
    """True si la cadena contiene al menos un número."""
    res = False
    for char in cad:
        if char.isdigit():
            res = True
    return res


def find_samples(directory):
    """Generador que busca en el directorio todos los ficheros .txt.
    """
    # pylint: disable=unused-variable
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(".txt"):
                fullpath = os.path.join(dirpath, filename)
                yield fullpath


def parse_granza(cad):
    """Trata de extraer y devolver de la cadena `cad`, que contiene lote y tipo
    de granza (no siempre), el tipo de granza.
    """
    tokens = cad.split(" ")
    granza = ""
    if len(tokens) > 1:
        codlote = tokens[2]
        if any_number(codlote):
            # Efectivamente, es un código de lote.
            granza = " ".join(tokens[3:])
        else:
            granza = " ".join(tokens[2:])
    return granza


# pylint: disable=too-many-branches,too-many-statements
def parse_source(filepath):
    """Lee el contenido del fichero y extrae los valores. Devuelve una tupla
    con el lote (como cadena) y los valores de ese lote como diccionario.
    """
    res = {'fecha': None,
           'código': None,
           'lote': None,
           'granza': None,
           'nominal': None,
           'título': None,
           'CV título': None,
           'elong': None,
           'CV elong': None,
           'ten': None,
           'CV ten': None,
           'source': filepath}
    with open(filepath, encoding="8859") as fin:
        reader = csv.reader(fin, delimiter="\t")
        numlinea = 0
        try:
            for fila in reader:
                numlinea += 1
                if numlinea == 2:
                    res['fecha'] = fila[3].split()[0]
                    res['nominal'] = fila[12]
                    res['lote'] = fila[14].replace("\n", "")
                elif numlinea == 3:
                    if not check_fila3(fila):
                        numlinea -= 1
                        res['lote'] += " " + fila[0]
                        continue
                    else:   # EOState
                        try:
                            res['granza'] = parse_granza(res['lote'])
                        except IndexError:
                            print("Error analizando granza en", filepath)
                            res['granza'] = res['lote']
                        else:
                            res['lote'] = res['lote'].replace(res['granza'],
                                                              "")
                else:
                    if fila[0] == "Average":
                        res['título'] = fila[1]
                        res['elong'] = fila[3]
                        res['ten'] = fila[4]
                    elif fila[0] == "CV%":
                        res['CV título'] = fila[1]
                        res['CV elong'] = fila[3]
                        res['CV ten'] = fila[4]
        except UnicodeDecodeError:  # EOF malformed en algunos ficheros
            pass
    fecha = res['fecha']
    res['lote'] = res['lote'].strip()
    res['granza'] = res['granza'].strip()
    if res['lote'].startswith("0"):    # Solo pueden ser 001..018
        lote = res['lote']
        res['código'] = " " + lote.split()[0]
        res['lote'] = " ".join(lote.split()[1:])
    else:
        res['código'] = ''
    if res['granza'].upper().startswith("LO"):
        res['lote'], res['granza'] = res['granza'], res['lote']
    if not res['lote'].upper().startswith("LO"):
        res['granza'] = res['lote'] + " " + res['granza']
        res['lote'] = ""
    if len(res['lote'].split()) > 2:
        if res['lote'].split()[1] == "REPSOL":  # Caso especial... :'(
            res['granza'] = " ".join(res['lote'].split()[1:])
        else:
            res['lote'] = " ".join(res['lote'].split()[:2])
            res['granza'] = " ".join(res['lote'].split()[2:]) + " " + res['granza']
    return fecha, res


def parse_data(directory="samples"):
    """Abre todos los ficheros `.txt` y "parsea" los datos que contiene.
    Devuelve un diccionario por fecha con una lista que contiene
    los valores de fecha, granza, título nominal, media de título medido,
    coeficiente de variación (del título), elongación, coeficiente de
    variación (de la elongación), tenacidad y coeficiente de variación de la
    tenacidad.
    Por ejemplo:
    {'26/09/2016': [{'fecha': '26/09/2016',
                     'lote': 'LOTE 2378',
                     'granza': 'REPSOL 050',
                     'código': '001',
                     'nominal': 6.7,
                     'título': 6.3,
                     'CV título': 6.75,
                     'elong': 94.08,
                     'CV elong': 23.76,
                     'ten': 47.70,
                     'CV ten': 6.59},
                    {...}]
     ...}
    NOTA: La fecha (clave) y el valor de 'fecha' del diccionario que contiene
    es la misma.
    """
    res = defaultdict(lambda: [])
    for filesource in find_samples(directory):
        fecha, valores = parse_source(filesource)
        res[fecha].append(valores)
    return res


def dump(dicdata, filepath="out.csv"):
    """Construye una hoja de cálculo con los valores ordenados por fecha."""
    with open(filepath, "w") as fout:
        fieldnames = ('source', 'fecha', 'código', 'lote', 'granza', 'nominal',
                      'título', 'CV título', 'elong', 'CV elong', 'ten',
                      'CV ten')
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        # writer.writerow(['Fecha', 'Lote', 'Granza', 'Nominal (dtex)',
        #                  'Título (dtex)', 'CV% título',
        #                  'Elong (%)', 'CV% elong',
        #                  'Ten (cN/tex)', 'CV% elong'])
        writer.writeheader()
        fechas = sorted(dicdata.keys(),
                        key=lambda fecha: datetime.date(
                            *[int(i) for i in reversed(fecha.split("/"))]))
        for fecha in fechas:
            for lote in dicdata[fecha]:
                writer.writerow(lote)


def main():
    """Rutina principal."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--sourcedir")
    args = parser.parse_args()
    if args.sourcedir:
        data = parse_data(args.sourcedir)
    else:
        data = parse_data()
    dump(data)


if __name__ == "__main__":
    main()
