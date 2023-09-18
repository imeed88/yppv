import fitz
import re
import datetime
import io
import subprocess
from reportlab.lib.pagesizes import  A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Spacer, Paragraph, Table, TableStyle,PageBreak,Image, KeepTogether
from reportlab.platypus.flowables import KeepInFrame

from django.templatetags.static import static

import spacy




def open_pdf(pdf_path):
    doc = fitz.open(stream=pdf_path.read(), filetype="pdf")
    all_blocks = []
    docinfo = doc.metadata
    for page in doc:
        blocks = page.get_text("dict", flags=11)["blocks"]
        all_blocks.extend(blocks[1:])
    issuer=blocks[0]["lines"][0]["spans"][0]["text"]
    doc.close()
    return  docinfo['title'], issuer, all_blocks



def extract_maintenance_procedures(blocks):
    groups = []
    current_group = None
    old_group = None 
    instrct_bocks=blocks[1:-1]
    for block in instrct_bocks:
        for line in block["lines"]:
            if old_group is not None  :
                groups.append(old_group)
                old_group = None
            is_group = False
            line_texts = []
            for span in line["spans"]:
                span_font_size = span["size"]
                span_text = span["text"]
                line_texts.append(span_text)
                if span_font_size > 10:
                    is_group = True
            if is_group :
                old_group=current_group
                current_group = {"group_title": "".join(line_texts), "subgroup": []}
            elif current_group is not None and is_group is False:
                current_group["subgroup"].append("".join(line_texts))
    if current_group is not None:
        groups.append(current_group)
    maintenance_procedures=[]
    extension=None
    container=None
    current_mp = None



    container=' '.join(groups[0]['subgroup'])

    if 'utiliser l' in container.lower():
        extension = {"isextension": True, "extension_path": "","extension_instructions": [],"extension_anomalies": [],"extension_note": []}
        
        if 'test electrique' in container.lower():
             extension['extension_path'] = 'TE'

        elif 'pistolet' in container.lower():
            extension['extension_path'] = 'PT'
        
        elif 'clip' in container.lower():
            extension['extension_path'] = 'CC'
        
        elif 'tightening' in container.lower():
            extension['extension_path'] = 'VS'
        
        elif 'jigboard' in container.lower():
            extension['extension_path'] = 'JB'




    for group in groups :
        current_mp= {"procedure_name": group["group_title"], "procedure_type": [],"procedure_instructions":[]}

        if "Legende" in current_mp["procedure_name"]:
            current_mp["procedure_type"]= 0  
        
        elif ( any("OK / NOK" in item for item in group['subgroup']) or any("OK/NOK" in item for item in group['subgroup']) or any("I__I" in item for item in group['subgroup']) ) and ("legende" not in group["group_title"][0].lower()) :
            current_mp["procedure_type"]= 3
            operations = []
            operations_initator=True

            for line in group["subgroup"]:
                    line = line.replace("…", "")
                    line = line.replace("...", "_")
                    line = re.sub(r'\.\s+\.\.', '..', line)
                    line = re.sub(r'(\s+\.)|(\.\s+)', '.', line)

                    if operations_initator or line.strip().startswith(('00','01','02','03','04','05','06','07','08','09','10','11','12','13','14','15','16','17','18','19','20','21','22','23','24','25','26','27','28','29','30','31','32','33','34','35','36','37','38','39','40')):
                        operations.append(line)
                        operations_initator=False
                    else:
                        operations[-1] += " "+ line.strip()         
            mod_operations=[]
            for op_i in operations:
                if "_" in op_i[:5]:
                    op_i=op_i[:5].replace("_", " ")+op_i[5:]
                matches = re.findall(r'^(.*?)\.*?_', op_i)
                if matches:
                    mod_operations.append({'operation': re.sub(r'(\([^)]*)$', r'\1)', matches[0].strip()) + '.' ,'status':0})

            current_mp["procedure_instructions"] =  mod_operations
        
        elif  any("01 ....." in item for item in group['subgroup']) or any("01....." in item for item in group['subgroup'])  :
            current_mp["procedure_type"]= 2   
        
        else:
            current_mp["procedure_type"]= 1
            current_mp["procedure_instructions"] = group['subgroup']      
        maintenance_procedures.append(current_mp)
    return maintenance_procedures,extension



def extract_maintenance_header(blocks):
    keywords = ['order', 'ordertype', 'startdate', 'enddate', 'funct.location', 'equipment', 'modelnumber', 'manufact.serialnr.', 'inventorynr.', 'plannedtime', 'pmplannergrp', 'inspectionlot.']
    values = {}
    data=[]
    for line in blocks[0]["lines"]:
        for span in line["spans"]:
            data.append(span["text"])
    current_keyword = None
    for item in data:
        line_stripped = item.strip()
        if any(line_stripped.lower() == keyword.lower() for keyword in keywords):
            if current_keyword is not None:
                values[current_keyword]=" ".join(item_it for item_it in values[current_keyword]).strip()
            current_keyword = line_stripped
            values[current_keyword] = []
        elif current_keyword is not None:
            values[current_keyword].append(line_stripped)
        
    values[current_keyword]=" ".join(item_it for item_it in values[current_keyword]).strip()
    return values




def header_seperator(header):
    order=int(str(header['Order']))
    ordertype=header['Ordertype']
    startdate=datetime.datetime.strptime(header['Startdate'], "%d.%m.%Y").strftime("%Y-%m-%d")

    enddate=datetime.datetime.strptime(header['Enddate'], "%d.%m.%Y").strftime("%Y-%m-%d") 
    functlocation=header['Funct.location']
    equipment=header['Equipment']
    modelnumber=header['Modelnumber']
    manufactserialnr=header['Manufact.Serialnr.']
    inventorynr=header['Inventorynr.']
    plannedtime=header['Plannedtime']
    pmplannergrp=header['PMplannergrp']
    inspectionlot=header['Inspectionlot.']
    return order,ordertype,startdate,enddate,functlocation,equipment,modelnumber,manufactserialnr,inventorynr,plannedtime,pmplannergrp,inspectionlot




def create_pdf(order):
    buffer = io.BytesIO()  # Create a buffer to store the PDF data





    DefaultExtensions = [
    {
        'group': 'TE',
        'subgroups': [
            {
                'subgrouptitle': 'Points liés à la table de Test Et ses accessoires',
                'instructions': [
                    {'index': 1, 'instruction': 'Vérifier le nettoyage de toutes les CPs du test électrique'},
                    {'index': 2, 'instruction': 'Vérifier le nettoyage du filtre etde l’intérieur du testélectrique'},
                    {'index': 3, 'instruction': 'Vérifier l’Etat/la Fermeture des portes et la bache de couverture'},
                    {'index': 4, 'instruction': 'Vérifer l’Etat /la Présence des vis des CPs et le bon serrage'},
                    {'index': 5, 'instruction': 'Vérifier l’arrangement des fils, les cables électriques et flexibles pneumatique'},
                    {'index': 6, 'instruction': 'La pression d’air d’entré est de 6 bars (fuites doivent être éliminées)'},
                    {'index': 7, 'instruction': 'Tester les cartes de rack avec le mode ‘diagnostic’'},
                    {'index': 8, 'instruction': 'Tester la fonctionalité du lecteur code à barre'},
                    {'index': 9, 'instruction': 'Tester la fonctionnalité du compteur et du bouton start'},
                    {'index': 10, 'instruction': 'Vérifier l’éclairage à l’intérieur et à l’extérieur du TE'},
                    {'index': 11, 'instruction': 'Vérifier la présence de toutes les accessoire du TE'},
                    {'index': 12, 'instruction': 'Vérifier l’état de la plaque (plate surface) & Numérotation de la CP'},
                    {'index': 13, 'instruction': 'Relever et vérifier le compteur, s\'il atteind 850 000 Cycles, Informer le superviseur'}
                ]
            },
            {
                'subgrouptitle': 'Points liés aux CPs',
                'instructions': [
                    {'index': 14, 'instruction': 'Tester les maintients des CP & la fonctionalité du Bouton d’expulsion'},
                    {'index': 15, 'instruction': 'Vérifier l\'étanchiété de la CP(Pression de test ne doit pas dépasser 0.06Mpa=0.6 Bar)'},
                    {'index': 16, 'instruction': 'Tester la bonne détection de fuite (test d’étanchieté)'},
                    {'index': 17, 'instruction': 'Vérifer la fermeture des sécurité des connecteurs & le desserage des pins coding'},
                    {'index': 18, 'instruction': 'Vérifier l\'état, la présence, le niveau, le serrage et le type de pins de toutes les CPs'},
                    {'index': 19, 'instruction': 'Vérifier l’état des pin HLC, et changer s’ils sont endomagés'},
                    {'index': 20, 'instruction': 'Faire le nettoyage des supports des Pins à ressort Pushback de débris et tester la continuité'},
                    {'index': 21, 'instruction': 'Tester le bon fonctionnement des pins et des switchs de detection'},
                    {'index': 22, 'instruction': 'Vérifier la capabilité des ressorts push –back/ Pin à Ressort'},
                    {'index': 23, 'instruction': 'Vérifier l’endommagement des guidages'},
                    {'index': 24, 'instruction': 'Vérifier la pression des CPs ABS selon les spécifications du fournisseur'},
                    {'index': 25, 'instruction': 'Vérifier la fixation et l’alignement des blocs mobiles des CPs'},
                    {'index': 26, 'instruction': 'Vérifier l’endommagement des plaques d’ouverture des shunts pour les CPs de l’airbag'},
                    {'index': 27, 'instruction': 'Vérifier le bon branchement des fils de la mise à terre'}
                ]
            }
        ]
    },
    {
        'group': 'CC',
        'subgroups': [
            {
                'subgrouptitle': 'Table du CLIP CHECKER',
                'instructions': [
                    {'index': 1, 'instruction': 'Faire le Nettoyage de la tableau du Lay out'},
                    {'index': 2, 'instruction': 'Vérifier l\'Endommagement du tableau et de lay out'},
                    {'index': 3, 'instruction': 'Faire le nettoyage à l’intérieur du Clip checker'},
                    {'index': 4, 'instruction': 'Vérifier l\'Etat et la Fermeture des portes'},
                    {'index': 5, 'instruction': 'Vérifier la Fixation, l’endomagementet le rangement des cables et des tuyeaux'},
                    {'index': 6, 'instruction': 'Vérifier que la pression d’air d’entré est de 6 bars (fuites doivent être éliminées)'},
                    {'index': 7, 'instruction': 'Tester les cartes de rack avec le mode \'diagnostic\''},
                    {'index': 8, 'instruction': 'Vérifier la fonctionalité du lecteur code à barre'},
                    {'index': 9, 'instruction': 'Vérifier la fonctionnalité du compteur et du bouton start'},
                    {'index': 10, 'instruction': 'Vérifier la présence de toutes les accessoire du CLC et que l\'Eclairage est OK'},
                    {'index': 11, 'instruction': 'Vérifier la vérification de l’onduleur (Fonctionnement au minimum 5 min)'}
                    ]
                },
                {
                    'subgrouptitle': 'Contre-pièces et les outils d’assemblage',
                    'instructions': [

                    {'index': 13, 'instruction': 'Vérifier la fixation et l\'endommagement des outils d’assemblage (fourches, …)'},
                    {'index': 14, 'instruction': 'Vérifier la fixation et l\'endommagement des CPs de Grommet'},
                    {'index': 15, 'instruction': 'Vérifier la fixation et l\'endommagement des CPs des Clips'},
                    {'index': 16, 'instruction': 'Vérifier les stoppers (système devérrouillage) et les vérins'},
                    {'index': 17, 'instruction': 'Faire un test Short pour vérifier les micro switch des CPs'},
                    {'index': 18, 'instruction': 'Faire les fonctionnalité des LEDs'},
                    {'index': 19, 'instruction': 'Tester la fonctionnalité des détecteurs de couleur'},
                    {'index': 20, 'instruction': 'Vérifier la fonctionnalité du tampon et l’état du l’encre'},
                    {'index': 21, 'instruction': 'Vérifier le bon branchement des fils de la mise à terre'}
                ]
            }
        ]
    },
    {
        'group': 'BF',
        'subgroups': [
            {
                'subgrouptitle': 'Table du Test',
                'instructions': [
                    {'index': 1, 'instruction': 'Faire le Nettoyage de l’équipement'},
                    {'index': 2, 'instruction': 'Vérifier la fixation, l’endomagementet le rangement des cables et les tuyeaux'},
                    {'index': 3, 'instruction': 'Vérifier que la pression d’air d’entré est de 6 bars (fuites doivent être éliminées)'},
                    {'index': 4, 'instruction': 'Vérifier la fonctionalité du lecteur code à barre'},
                    {'index': 5, 'instruction': 'Vérifier la fonctionnalité de l\'éclairage de la caméra'},
                    {'index': 6, 'instruction': 'Vérifier la propreté et la fixation de la lentille de la caméra'},
                    {'index': 7, 'instruction': 'Accéder au dossier des photos prises par la caméra et vérifier la qualité des dernières photos prises'},
                    {'index': 8, 'instruction': 'Vérifier la fonctionalité des detecteurs magnétiques (S\'ils existent)'},
                    {'index': 9, 'instruction': 'Vérifier la fonctionalité des points de detection de l’insertion des fusibles'},
                    {'index': 10, 'instruction': 'Vérifier la fixation de toutes les parties mécaniques'},
                    {'index': 11, 'instruction': 'Tester le bon fonctionnement de la fonction "Bonne insertion" en faisant une simulation avec des relais et fusibles non complétement inséré et vérifier la détection de la non insertion'},
                    {'index': 12, 'instruction': 'Vérifier le bon branchement des fils de la mise à terre'}
                ]
            }
        ]
    },
    {
        'group': 'PT',
        'subgroups': [
            {
                'subgrouptitle': 'Points génériques',
                'instructions': [
                    {'index': 1, 'instruction': 'Faire le nettoyage de l\'intérieur et l\'extérieur de l’imprimante'},
                    {'index': 2, 'instruction': 'Faire un test du clavier'},
                    {'index': 3, 'instruction': 'Assurer la fixation du capot de la machine et des pieds en plastique'}
                    
                ]
            },
            {
                'subgrouptitle': 'Mécanisme de transmission de l’étiquette',
                'instructions': [
        {'index': "SP", 'instruction': 'SP'},
                    {'index': 4, 'instruction': 'Vérifier l\'Enrouleur des étiquettes "L" et la fixation du disque "K"'},
                    {'index': 5, 'instruction': 'Vérifier l\'enrouleur du Ruban'},
                    {'index': 6, 'instruction': 'Vérifer la Photocellule "I"'},
                    {'index': 7, 'instruction': 'Vérifier le mécanisme de pression "H"'},
                    {'index': 8, 'instruction': 'Vérifier le distributeur des étiquettes "N"'},
                    {'index': 9, 'instruction': 'Vérifier les accessoires de guidage "J"'},
                    {'index': 10, 'instruction': 'Vérifier la rête thermique "D" (Tous les segments sont visibles après un test d’impression)'},
                    {'index': 11, 'instruction': 'Vérifier la mécanisme de fixation de la tête thermique "E"'}
                ]
            }
        ]
    },
    {
        'group': 'JB',
        'subgroups': [
            {
                'subgrouptitle': 'Points à vérifier durant la maintenance préventive périodique',
                'instructions': [
                    {'index': 1, 'instruction': 'Vérifiez si les jigboards sont bien fixés et ne bougent pas'},
                    {'index': 2, 'instruction': 'Vérifier si tous les trous sont fermés'},
                    {'index': 3, 'instruction': 'Vérifiez si les jigboards sont propres, pas de poussière'},
                    {'index': 4, 'instruction': 'Informations visuelles\nVérifier si les dessins et les symboles de l\'aide imprimés sur le dessin-layout sont lisibles, pas d\'endommagement'},
                    {'index': 5, 'instruction': 'Vérification générale de tous les outils jig\n- Tous les outils des jigs doivent correspendre à leurs codes sur le dessin Lay out\n- Tous les outils jig doivent être bien fixés (Aucun desserage n\'est autorisé)\n- Vérifier s\'il n\'y a aucun endommagement, aucune cassure et aucune arête vive\n- Tous les outils doivent être fixés perpendiculairement sur le jig-board (avec un angle de 90 degrés)'},
                    {'index': 6, 'instruction': 'Vérifier toutes les fourches (fixes et rabattables(Updown))\n- Les pins et les support pins doivent être droits (pas d\'inclinaison)\n- Les fourches rabattable (updown) doivent fonctionner correctement'},
                    {'index': 7, 'instruction': 'Vérifier tous les pin fourches connecteurs (fixe et rabattable -fall down forks-)\n- Tous les pins doivent avoir des stoppers et des arrières-connecteurs\n- Tous les pins doivent être droits et Il ne manque aucun pin\n- Les fourche rabattable (fall down) doivent fonctionner correctement'},
                    {'index': 8, 'instruction': 'Vérifier toutes les contres-pièces des connecteurs, grommets et Protecteurs\n-Vérifier s\'il n\'y a pas de poussière à l\'intérieur des contres-pièces\n-Vérifier si le dispositif de verrouillage (Stopper) fonctionne correctement\n- Vérifier le bon serrage des vis'},
                    {'index': 9, 'instruction': 'Vérifier tous les clip holders\n- Orientation correcte\n- Les support doivent être droits'},
                    {'index': 10, 'instruction': 'Vérifier toutes les languettes (Indicators)\n-Toutes les longuettes doivent être droites'},
                    {'index': 11, 'instruction': 'Vérifier tous les séparateurs (wire holder)\n- Les pins doivent fonctionner correctement'}
                ]
            }
        ]
    },
    {
        'group': 'VS',
        'subgroups': [
            {
                'subgrouptitle': 'Table du Test',
                'instructions': [
                    {'index': 1, 'instruction': 'Faire le Nettoyage de l’équipement (Tables & CPs)'},
                    {'index': 2, 'instruction': 'Vérifier la fixation, l’endomagement et le rangement des cables et les tuyeaux'},
                    {'index': 3, 'instruction': 'Vérifier que la pression d’air d’entré est de 6 bars (fuites doivent être éliminées)'},
                    {'index': 4, 'instruction': 'Vérifier la fonctionalité du lecteur code à barre'},
                    {'index': 5, 'instruction': 'Vérifier l’éclairage à l’intérieur et à l’extérieur du TE'},
                    {'index': 6, 'instruction': 'Vérifier l’état de la plaque (plate surface) & Numérotation de la CP'},
                    {'index': 7, 'instruction': 'Vérifier la fixation l\'usure et la fonctionnalité du module de la sélection de l’outil'},
                    {'index': 8, 'instruction': 'Vérifier l’onduleur (Fonctionne au minimum 5 min)'}
                ]
            },
            {
                'subgrouptitle': 'Test Caméra et les détecteurs',
                'instructions': [
                    {'index': 9, 'instruction': 'Vérifier la fixation, l\'usure et la fonctionnalité des capteurs de proximité (S\'ils existent)'},
                    {'index': 10, 'instruction': 'Vérifier la propreté et la fixation de la lentille de la caméra'},
                    {'index': 11, 'instruction': 'Accéder au dossier des photos prises par la caméra et vérifier la qualité des dernières photos prises'},
                    {'index': 12, 'instruction': 'Vérifier la fixation, l\'usure et la fonctionnalité des maintiens des Contres-pièces'},
                    {'index': 13, 'instruction': 'Vérifier la présence, le niveau, le serrage et le type de pins de toutes les CPs'},
                    {'index': 14, 'instruction': 'Tester le bon fonctionnement des pins et des switchs de detection'}
                ]
            },
            {
                'subgrouptitle': 'Test de la visseuse',
                'instructions': [
                    {'index': 15, 'instruction': 'Vérifier le serrage de toutes les Vis de la visseuse'},
                    {'index': 16, 'instruction': 'Vérifier l\'état et le fonctionnement des capteurs linéaires et angulaires (S\'ils existent)'},
                    {'index': 17, 'instruction': 'Vérifier la fixation et l\'état du coffret de la visseuse (Afficheur, Boutons)'},
                    {'index': 18, 'instruction': 'Vérifier la fonctionnalité des LEDs et du bouton poussoir de la broche'},
                    {'index': 19, 'instruction': 'Vérifier le support de la broche (Visseuse) et la pince de fixation (Pas d\'endommagement)'},
                    {'index': 20, 'instruction': 'Faire un test de vissage et de dévissage et contôler le fonctionnement en mode normal (pas de bruit ou température excessive au niveau la broche de la visseuse'},
                    {'index': 21, 'instruction': 'Contrôler la date de calibrage de la broche'},
                    {'index': 22, 'instruction': 'Vérifier le bon branchement des fils de la mise à terre'}
                ]
            }
        ]
    }
    ]





    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=32, rightMargin=32, topMargin=32, bottomMargin=32)




    docinfo = order['docinfo']
    status = order['status']
    issuer = order['issuer']
    orderref = order['orderref']
    personorderd = order['personorderd']
    grouporderd = order['grouporderd']
    week = order['week']
    ordertype = order['ordertype']
    startdate = order['startdate']
    enddate = order['enddate']
    submitdate = order['submitdate']

    plannedtime = order['plannedtime']
    pmplannergrp = order['pmplannergrp']
    inspectionlot = order['inspectionlot']
    instructions = order['instructions']
    extension = order['extension']



    inventorynr = order['equipment']['inventorynr']
    nomenclature = order['equipment']['nomenclature']
    modelnumber = order['equipment']['modelnumber']
    manufactserialnr = order['equipment']['manufactserialnr']
    inventoryref = order['equipment']['inventoryref']
    functlocation = order['equipment']['functlocation'] if order['equipment']['functlocation'] else None



    custom_gray = colors.Color(0.95, 0.95, 0.95)
    custom_red = colors.Color(1, 0.129, 0.086)
    custom_green = colors.Color(0, 0.859, 0)
    custom_yellow = colors.Color(0.99, 0.98, 0.87)
    custom_blue = colors.Color(0.035, 0.118, 0.259)
    custom_blue2 = colors.Color(0.016, 0.055, 0.118)

    style = ParagraphStyle(
        name="CustomStyle",
        fontName="Helvetica-Bold", 
        fontSize=14,
        leading=14,
        textColor=custom_blue
    )


    style_title = ParagraphStyle(
        name="CustomStyle",
        fontName="Helvetica-Bold", 
        fontSize=15,
        leading=14,
        textColor=custom_blue
    )

    style_op = ParagraphStyle(
        name="CustomStyle",
        fontName="Helvetica", 
        fontSize=11.5,
        leading=15,
        textColor=custom_blue2
    )

    style_sts = ParagraphStyle(name="status_style", alignment=1, textColor=colors.white,
        fontName="Helvetica-Bold", ) 




    style_op_ext = ParagraphStyle(
        name="CustomStyle",
        fontName="Helvetica", 
        fontSize=8.5,
        textColor=custom_blue2
    )





    style_group_ext = ParagraphStyle(
        name="CustomStyle",
        fontName="Helvetica-Bold", 
        fontSize=10,
        textColor=custom_blue2
    )



    style_extention_title = ParagraphStyle(
        name="CustomStyle",
        fontName="Helvetica-Bold", 
        fontSize=10.7,
        alignment=1,
        textColor=custom_blue2
    )


    style_extention_title_2 = ParagraphStyle(
        name="CustomStyle",
        fontName="Helvetica-Bold", 
        fontSize=9,
        alignment=1,
        textColor=custom_blue2
    )



    act=0
    act_corr=0

    
    main_table = []

    for item in instructions:
        
        procedure_name = item["procedure_name"]
        procedure_type = item["procedure_type"]
        procedure_instructions = item["procedure_instructions"]
        
        title_table = Table([[Paragraph(procedure_name, style)]],colWidths=[530])
        title_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), custom_yellow),]))

        main_table.append([Spacer(0, 5)])
        main_table.append([title_table])



            
        if procedure_type in (0, 1):
            informative_text = "\n".join(procedure_instructions)  
            informatibe_table = Table([[Paragraph(informative_text, style_op)]],colWidths=[530])
            main_table.append([informatibe_table])
        elif procedure_type == 2:
            fillable_form = "\n".join(procedure_instructions.strip().split("\n"))
            fillable_form_table = Table([[fillable_form]], colWidths=[510])
            
            fillable_form_table.setStyle([("BOX", (0, 0), (0, 0), 1, custom_gray),
                                        ("TEXTCOLOR", (0, 0), (0, 0), custom_blue2),
                                        ("FONTSIZE", (0, 0), (0, 0), 11.5),
                                        ("LEADING", (0, 0), (0, 0), 15), ])
            fillable_form_table.hAlign = 'CENTER'
            main_table.append([fillable_form_table])

        elif procedure_type == 3:
            table_data = [] 
            
            for instr in procedure_instructions:
                operation = instr["operation"]
                status = instr["status"]
                act+=1
                
                if status == "1":
                    status_text = "NA"
                    act_corr+=1
                elif status == "2":
                    status_text = "NOK"
                    act_corr+=1
                elif status == "3":
                    status_text = "OK"
                else:
                    status_text = ""
                status_par = Paragraph(status_text,style_sts)
                operation_par = Paragraph(operation,style_op)
                table_data.append([operation_par, status_par])
            
            
            if table_data:
                table = Table(table_data,style=None, colWidths=[450, 60])
                table.hAlign = 'CENTER'
                table.setStyle(TableStyle([('VALIGN', (1, 0), (1, -1), 'MIDDLE'),]))  

                for index, instr in enumerate(procedure_instructions):
                    status = instr["status"]
                    if status == "1":
                        cell_color = colors.orange
                    elif status == "2":
                        cell_color = custom_red
                    elif status == "3":
                        cell_color = custom_green
                    else:
                        cell_color = colors.white   

                    table.setStyle([('BACKGROUND', (1, index), (1, index), cell_color)])

            table.setStyle([
                    ('LINEABOVE', (0, 0), (-1, 0), 1, custom_gray),  # First row's horizontal line
                    ('LINEBELOW', (0, 0), (-1, -1), 1, custom_gray),  # Last row's horizontal line
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.red),  # Text color for the first row
                ])
                    

            main_table.append([table]) 











 
    

    if extension:    
        extension_instructions=extension['extension_instructions']


        te_subgroups = next(group['subgroups'] for group in DefaultExtensions if group['group'] == extension['extension_path'])



        instruction_table_elements = []

        for  instruction_idx, subgroup in  enumerate(te_subgroups):
            table_data = [] 

            
            subgroup_data=subgroup['instructions']
            extension_value = extension_instructions[instruction_idx]['value']
            extension_comment = extension_instructions[instruction_idx]['comms']

            instruction_table_elements.append([" ", [Paragraph(subgroup['subgrouptitle'], style_group_ext)],"",""])
            

            for instruction_jdx, instruction_data in enumerate(subgroup_data):
                
                status=extension_value[instruction_jdx]
                index = instruction_data['index']
                instruction = instruction_data['instruction']
                try:
                    comment = extension_comment[instruction_jdx]
                    if comment is None:
                        comment = ""
                except IndexError:
                    comment = ""

                extension_comment = [comment if comment is not None else "" for comment in extension_comment]
                act+=1

                if status == "1":
                    status_text = "NA"
                    act_corr+=1
                elif status == "2":
                    status_text = "NOK"
                    act_corr+=1
                elif status == "3":
                    status_text = "OK"
                else:
                    status_text = ""
                
                
                status_par = Paragraph(status_text,style_sts)
                operation_par = Paragraph(instruction,style_op_ext)
                index_par = Paragraph(str(index),style_op_ext)
                comment_par = Paragraph(comment,style_op_ext)

                instruction_table_elements.append([index_par,operation_par, status_par,comment_par])
                
        extension_table = Table(instruction_table_elements,style=None, colWidths=[25,315,45,135])


        cumulative_instruction_dx = 0
    
        for  instruction_idx, subgroup in  enumerate(te_subgroups):
            
            subgroup_data=subgroup['instructions']
            extension_value = extension_instructions[instruction_idx]['value']


            for instruction_jdx, instruction_data in enumerate(subgroup_data):
                
                status=extension_value[instruction_jdx]
                
                if status == "1":
                    status_text = "NA"
                    cell_color = colors.orange
                elif status == "2":
                    status_text = "NOK"
                    cell_color = custom_red
                elif status == "3":
                    status_text = "OK"
                    cell_color = custom_green
                else:
                    status_text = ""
                    cell_color = colors.white
                
                cumulative_instruction_dx += 1
                extension_table.setStyle([('BACKGROUND', (2, cumulative_instruction_dx), (2, cumulative_instruction_dx), cell_color)])

            cumulative_instruction_dx += 1

        extension_table.setStyle([("BOX", (0, 0), (-1, -1), 1, colors.black),
                        ('INNERGRID', (0,0), (-1,-1), 1, colors.black),
                        ('LEADING', (0, -1), (-1, -1), 35)])

            
        extention_title_elements=[]


        extention_title_elements.append([Paragraph("Points à vérifier durant la maintenance préventive périodique", style_extention_title),Paragraph("Status", style_extention_title),Paragraph("Commentaire", style_extention_title)])


        extension_title_table = Table(extention_title_elements,style=None, colWidths=[340,45,135])

        extension_title_table.setStyle([("BOX", (0, 0), (-1, -1), 1, colors.black),
                            ('INNERGRID', (0,0), (-1,-1), 1, colors.black),
                                ('ALIGN',(0, 0), (-1, -1),'CENTER')])

        extension_title_table.hAlign = 'CENTER'

        extention_anomalies_title_elements=[]
        extention_anomalies_title_elements.append([Paragraph("Liste des anomalies et les contre-mesures", style_extention_title)])
        extention_anomalies_title_table = Table(extention_anomalies_title_elements,style=None, colWidths=[520])

        extention_anomalies_title_table.setStyle([('ALIGN',(0, 0), (-1, -1),'RIGHT'),
                                                ("BOX", (0, 0), (-1, -1), 1, colors.black),])

        extention_note_elements=[]
        extention_note_elements.append([ Paragraph("Note :",style_extention_title), Paragraph(extension['extension_note'].replace('\n','<br />\n'))])

        extension_note_table = Table(extention_note_elements,style=None, colWidths=[45,475])
        extension_note_table.setStyle([("BOX", (0, 0), (-1, -1), 1, colors.black),
                            ('VALIGN',(0,0),(-1, -1),'TOP'),
                                ('LEADING', (0, -1), (-1, -1), 35)])
        

        extension_anomalies = extension['extension_anomalies']
        anomalies_table_elements = []
        anomalies_table_elements.append([Paragraph("ID", style_extention_title_2), 
                                        Paragraph("Partie concernée", style_extention_title_2), 
                                        Paragraph("Etat (Avant réparation)", style_extention_title_2), 
                                        Paragraph("Action en cas d’anomalie", style_extention_title_2), 
                                        Paragraph("Etat (Après réparation)", style_extention_title_2)])



        if extension_anomalies :
            for idx, anomaly in enumerate(extension_anomalies, start=1):
                anomalies_row_data=[]
                anomalies_row_data.append(Paragraph(str(idx), style_op_ext))
                for element in anomaly:
                    data_paragraph = Paragraph(str(element), style_op_ext)
                    anomalies_row_data.append(data_paragraph)

                anomalies_table_elements.append(anomalies_row_data)
        else:
            anomalies_table_elements.append(["","","",""])
            

        extension_anomalies_table = Table(anomalies_table_elements, style=None, colWidths=[25, 124, 123, 124, 124])

        extension_anomalies_table.setStyle([("BOX", (0, 0), (-1, -1), 1, colors.black),
                            ('INNERGRID', (0,0), (-1,-1), 1, colors.black)])







        

    image_url = "https://i.ibb.co/44j9KtW/yzki-logo-bck-sm.png"
    
    titletable = Table(
        [[Paragraph("Formulaire d'Intervention de Maintenance Préventive", style_title), Image(image_url, width=102, height=16)],],
        style=None,
        colWidths=[416, 104]
    )


    titletable.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),]))



    header_table_elements = []
    header_table_elements.append(["Réf. consigne", str(orderref)])
    header_table_elements.append(["Emise par", str(issuer.split(" ")[-1])])
    header_table_elements.append(["Semaine", str(week)])
    header_table_elements.append(["Échéance", str(enddate)])
    header_table_elements.append(["Équipement", str(inventorynr)])
    header_table_elements.append(["Réf. équipement", str(nomenclature)])
    header_table_elements.append(["Loc. fonctionnelle", str(functlocation)])
    header_table_elements.append(["Effectué par", str(personorderd)])
    header_table_elements.append(["Effectué le", str(submitdate)])
    headtable = Table(header_table_elements,style=None, colWidths=[300,220])






    score = (act-act_corr) / act
    percentage = "{:.2%}".format(score)
    score_table_elements = [["Score", percentage, "Actions", act_corr]]
    scoretable = Table(score_table_elements, style=None, colWidths=[100, 300, 80, 45],rowHeights=[20],)
    scoretable.setStyle([('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey)])
    scoretable.setStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (0, -1), 11),
        ('VALIGN',(0, 0), (0, -1),'MIDDLE'),
        ('TEXTCOLOR', (0, 0), (0, -1), custom_blue),
        ('FONT', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (1, -1), 11),
        ('VALIGN',(1, 0), (1, -1),'MIDDLE'),
        ('TEXTCOLOR', (1, 0), (1, -1), custom_blue),
        ('FONT', (2, 0), (2, -1), 'Helvetica'),
        ('FONTSIZE', (2, 0), (2, -1), 11),
        ('VALIGN', (2, 0), (2, -1), 'MIDDLE'),
        ('TEXTCOLOR', (2, 0), (2, -1), custom_blue),
        ('FONT', (3, 0), (3, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (3, 0), (3, -1), 11),
        ('VALIGN', (3, 0), (3, -1), 'MIDDLE'),
        ('TEXTCOLOR', (3, 0), (3, -1), custom_blue)
    ])
    scoretable.hAlign = 'CENTER'



    stories = []

    stories.extend([titletable, Spacer(0, 15), scoretable, Spacer(0, 5), headtable, Spacer(0, 25)])

    for element in main_table:
        stories.extend(element)

    if extension :
        stories.append(PageBreak())
        stories.extend([titletable,Spacer(0, 15), scoretable,Spacer(0, 5),extension_title_table,extension_table,extention_anomalies_title_table,extension_anomalies_table,extension_note_table])
        
    
    doc.build(stories)




    pdf_data = buffer.getvalue() 



    return pdf_data




import copy

def clean_orders(instructions):
    operations = []

    for procedure in instructions:
        if procedure["procedure_type"] == 3:
            for instruction in procedure["procedure_instructions"]:
                operation_text = re.sub(r'^\d+\s*', '', instruction["operation"])
                operations.append({"operation": operation_text, "status": instruction["status"]})

    return operations

import spacy

nlp = spacy.load("fr_core_news_sm")

def create_ohr(orders):


    for order in orders:
        order['instructions'] = clean_orders(order['instructions'])

    base_order = max(orders, key=lambda x: len(x['instructions']))
    base_order_operations = [op["operation"] for op in base_order['instructions']]



    print(base_order_operations)
    for order in orders:
        
        order_operations = [op["operation"] for op in order['instructions']]
        order_status=[op["status"] for op in order['instructions']]








   
 
    return 0




