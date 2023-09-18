
from datetime import date,datetime
from django.contrib import messages
from django.contrib.auth import logout,login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import IntegrityError
from django.db.models import Q ,Value, CharField
from .models import order,group,userprofile,equipment

from django.db.models.functions import Concat
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render , redirect
from django.utils import timezone

from .converters import create_pdf, open_pdf, extract_maintenance_procedures, extract_maintenance_header, header_seperator, create_ohr

import json
import io
import PyPDF2









@login_required
def index(request):
    return render(request, 'apgmp/index.html')



@login_required
def orderform(request, order_ref, order_id):
    return render(request, 'apgmp/orderform.html', {'order_ref': order_ref, 'order_id': order_id})



def equipmentform(request, equipement_invnr):
    return render(request, 'apgmp/equipmentform.html', {'equipement_invnr': equipement_invnr,})




@login_required
def selector(request):
    return render(request, 'apgmp/selector.html')

@login_required
def upload(request):
    return render(request, 'apgmp/upload.html')

def download(request):
    return render(request, 'apgmp/download.html')



@login_required
def adminupanel(request):
    return render(request, 'apgmp/adminupanel.html')




@login_required
def adminopanel(request):
    return render(request, 'apgmp/adminopanel.html')




@login_required
def adminepanel(request):
    return render(request, 'apgmp/adminepanel.html')




@login_required
def order_load(request): 
    order_ref = request.GET.get('orderRef')
    order_id = request.GET.get('orderId')
    if order_ref and order_id:
        order_obj = order.objects.select_related('equipment').filter(id=order_id, orderref=order_ref).first()
        order_i = {
                'id': order_obj.id,
                'docinfo': order_obj.docinfo,
                'status': order_obj.status,
                'issuer': order_obj.issuer,
                'orderref': order_obj.orderref,
                'personorderd': order_obj.personorderd,
                'grouporderd': order_obj.grouporderd,
                'week': order_obj.week,
                'ordertype': order_obj.ordertype,
                'startdate': order_obj.startdate.strftime('%Y-%m-%d') if order_obj.startdate else None,
                'enddate': order_obj.enddate.strftime('%Y-%m-%d') if order_obj.enddate else None,
                'submitdate': order_obj.submitdate.strftime('%Y-%m-%d') if order_obj.submitdate else None,
                'equipment': {
                    'inventorynr': order_obj.equipment.inventorynr,
                    'nomenclature': order_obj.equipment.nomenclature,
                    'modelnumber': order_obj.equipment.modelnumber,
                    'manufactserialnr': order_obj.equipment.manufactserialnr,
                    'inventoryref': order_obj.equipment.inventoryref,
                    'functlocation': order_obj.equipment.functlocation[-1] if order_obj.equipment.functlocation else None
                },
                'plannedtime': order_obj.plannedtime,
                'pmplannergrp': order_obj.pmplannergrp,
                'inspectionlot': order_obj.inspectionlot,
                'instructions': order_obj.instructions,
                'extension': order_obj.extension,
            }
        



    return JsonResponse({'order': order_i})




def reduced_orders_load(request):
    
    user = request.user
    today = date.today()
    orders = order.objects.filter(grouporderd__in=user.userprofile.group, startdate__lte=today ,status=False).defer('instructions', 'extension')
    return JsonResponse({'orders': list(orders.values())})


 



def reduced_orders_load_reduced_to_equipement(request):
    equipementId = request.GET.get('equipementId')
    
    if equipementId is None:
        return JsonResponse({'error': 'equipementInvnr parameter is required'}, status=400)
    
    
    
    equipement = get_object_or_404(equipment, id=equipementId)
    
    equipement_data = {
        'inventorynr': equipement.inventorynr,
        'nomenclature': equipement.nomenclature,
        'modelnumber': equipement.modelnumber,
        'manufactserialnr': equipement.manufactserialnr,
        'inventoryref': equipement.inventoryref,
        'functlocation': equipement.functlocation,
    }


    orders = order.objects.filter(equipment=equipementId)

    # Process orders
    processed_orders = []
    for order_obj in orders:
        order_i = {
                'id': order_obj.id,
                'status': order_obj.status,
                'issuer': order_obj.issuer,
                'orderref': order_obj.orderref,
                'personorderd': order_obj.personorderd,
                'grouporderd': order_obj.grouporderd,
                'week': order_obj.week,
                'ordertype': order_obj.ordertype,
                'startdate': order_obj.startdate.strftime('%Y-%m-%d') if order_obj.startdate else None,
                'enddate': order_obj.enddate.strftime('%Y-%m-%d') if order_obj.enddate else None,
                'submitdate': order_obj.submitdate.strftime('%Y-%m-%d') if order_obj.submitdate else None,


        }
        processed_orders.append(order_i)

    return JsonResponse({'equipement': equipement_data,'orders': processed_orders})



 

def reduced_orders_load_to_expired_selector(request):
    user = request.user

    # Get the user's group from the user profile
    try:
        user_profile = user.userprofile
        user_groups = user_profile.group
    except user.userprofile.DoesNotExist:
        user_groups = []

    today = date.today()



    sorting_parameter = request.GET.get('sort', 'week')
    sortorder = request.GET.get('sortorder', 'asc')
    

    if sortorder == 'desc':
            sorting_parameter = '-' + sorting_parameter 


    orders = order.objects.filter(status=False,grouporderd__in=user_groups, enddate__lt=today).select_related('equipment').order_by(
        sorting_parameter , 'week', 'equipment__functlocation', 'equipment__nomenclature'
    ).defer('instructions', 'extension')




    items_per_page = 50
    paginator = Paginator(orders, items_per_page)

    page = request.GET.get('page', 1)
    

    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)

    # Process orders for the current page
    processed_orders = []
    total_pages = paginator.num_pages


    for order_obj in orders_page:
 
        order_i = {
                'id': order_obj.id,
                'docinfo': order_obj.docinfo,
                'status': order_obj.status,
                'issuer': order_obj.issuer,
                'orderref': order_obj.orderref,
                'personorderd': order_obj.personorderd,
                'grouporderd': order_obj.grouporderd,
                'week': order_obj.week,
                'ordertype': order_obj.ordertype,
                'startdate': order_obj.startdate.strftime('%Y-%m-%d') if order_obj.startdate else None,
                'enddate': order_obj.enddate.strftime('%Y-%m-%d') if order_obj.enddate else None,
                'submitdate': order_obj.submitdate.strftime('%Y-%m-%d') if order_obj.submitdate else None,
                'equipment': {
                    'inventorynr': order_obj.equipment.inventorynr,
                    'nomenclature': order_obj.equipment.nomenclature,
                    'modelnumber': order_obj.equipment.modelnumber,
                    'manufactserialnr': order_obj.equipment.manufactserialnr,
                    'inventoryref': order_obj.equipment.inventoryref,
                    'functlocation': order_obj.equipment.functlocation if order_obj.equipment.functlocation else None
                },
                'plannedtime': order_obj.plannedtime,
                'pmplannergrp': order_obj.pmplannergrp,
                'inspectionlot': order_obj.inspectionlot,
                'instructions': order_obj.instructions,
                'extension': order_obj.extension,
            }

        processed_orders.append(order_i)


    return JsonResponse({'orders': processed_orders, 'total_pages': total_pages})






def reduced_orders_load_to_current_selector(request):
    user = request.user

    try:
        user_profile = user.userprofile
        user_groups = user_profile.group
    except user.userprofile.DoesNotExist:
        user_groups = []

    today = date.today()



    sorting_parameter = request.GET.get('sort', 'week')
    sortorder = request.GET.get('sortorder', 'asc')
    

    if sortorder == 'desc':
            sorting_parameter = '-' + sorting_parameter 


    orders = order.objects.filter(status=False,grouporderd__in=user_groups, startdate__lte=today, enddate__gte=today).select_related('equipment').order_by(
        sorting_parameter , 'week', 'equipment__functlocation', 'equipment__nomenclature'
    ).defer('instructions', 'extension')




    items_per_page = 50
    paginator = Paginator(orders, items_per_page)

    page = request.GET.get('page', 1)

    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)

    # Process orders for the current page
    processed_orders = []
    total_pages = paginator.num_pages


    for order_obj in orders_page:
 
        order_i = {
                'id': order_obj.id,
                'docinfo': order_obj.docinfo,
                'status': order_obj.status,
                'issuer': order_obj.issuer,
                'orderref': order_obj.orderref,
                'personorderd': order_obj.personorderd,
                'grouporderd': order_obj.grouporderd,
                'week': order_obj.week,
                'ordertype': order_obj.ordertype,
                'startdate': order_obj.startdate.strftime('%Y-%m-%d') if order_obj.startdate else None,
                'enddate': order_obj.enddate.strftime('%Y-%m-%d') if order_obj.enddate else None,
                'submitdate': order_obj.submitdate.strftime('%Y-%m-%d') if order_obj.submitdate else None,
                'equipment': {
                    'inventorynr': order_obj.equipment.inventorynr,
                    'nomenclature': order_obj.equipment.nomenclature,
                    'modelnumber': order_obj.equipment.modelnumber,
                    'manufactserialnr': order_obj.equipment.manufactserialnr,
                    'inventoryref': order_obj.equipment.inventoryref,
                    'functlocation': order_obj.equipment.functlocation if order_obj.equipment.functlocation else None
                },
                'plannedtime': order_obj.plannedtime,
                'pmplannergrp': order_obj.pmplannergrp,
                'inspectionlot': order_obj.inspectionlot,
                'instructions': order_obj.instructions,
                'extension': order_obj.extension,
            }

        processed_orders.append(order_i)

    

    return JsonResponse({'orders': processed_orders, 'total_pages': total_pages})





def orders_load(request):

    e_filters = {}  # For equipment
    o_filters = {}  # For order

    field_mapping = {
    'inventorynr',
    'nomenclature',
    'functlocation',
    'week',
    'orderref',
    'grouporderd',
    }

    for field in field_mapping:
        value = request.GET.get(field)
        if value is not None and value != '':
            if field in {'inventorynr', 'nomenclature', 'functlocation'}:
                e_filters[f"{field}__icontains"] = value
            else:
                o_filters[f"{field}__icontains"] = value



    equipments = equipment.objects.filter(**e_filters)
    equipment_ids = equipments.values_list('id', flat=True)
    o_filters['equipment__in'] = equipment_ids

    checkboxorderincomp = request.GET.get('checkboxorderincomp', 'true') == 'true'
    checkboxorderinprocess = request.GET.get('checkboxorderinprocess', 'true') == 'true'


    loader=True




    sorting_parameter = request.GET.get('sort', 'week')
    sortorder = request.GET.get('sortorder', 'asc')
    

    if sortorder == 'desc':
            sorting_parameter = '-' + sorting_parameter 






    if checkboxorderincomp and checkboxorderinprocess:
        # Load all orders, regardless of status
        pass
    elif checkboxorderincomp:
        # Load orders where order.status is True
        o_filters['status'] = True
    elif checkboxorderinprocess:
        # Load orders where order.status is False
        o_filters['status'] = False
    else:
        loader=False

    if loader :
        orders = order.objects.filter(**o_filters).select_related('equipment').order_by(            
            sorting_parameter , 'week', 'equipment__functlocation', 'equipment__nomenclature').defer('instructions', 'extension')
         
    else :
        orders= []


  



        


    items_per_page = 50 
    paginator = Paginator(orders, items_per_page)

    page = request.GET.get('page', 1) 

    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)

    # Process orders for the current page
    processed_orders = []
    total_pages = paginator.num_pages


    for order_obj in orders_page:
 
        order_i = {
                'id': order_obj.id,
                'docinfo': order_obj.docinfo,
                'status': order_obj.status,
                'issuer': order_obj.issuer,
                'orderref': order_obj.orderref,
                'personorderd': order_obj.personorderd,
                'grouporderd': order_obj.grouporderd,
                'week': order_obj.week,
                'ordertype': order_obj.ordertype,
                'startdate': order_obj.startdate.strftime('%Y-%m-%d') if order_obj.startdate else None,
                'enddate': order_obj.enddate.strftime('%Y-%m-%d') if order_obj.enddate else None,
                'submitdate': order_obj.submitdate.strftime('%Y-%m-%d') if order_obj.submitdate else None,
                'equipment': {
                    'inventorynr': order_obj.equipment.inventorynr,
                    'nomenclature': order_obj.equipment.nomenclature,
                    'modelnumber': order_obj.equipment.modelnumber,
                    'manufactserialnr': order_obj.equipment.manufactserialnr,
                    'inventoryref': order_obj.equipment.inventoryref,
                    'functlocation': order_obj.equipment.functlocation[0] if order_obj.equipment.functlocation else None
                },
                'plannedtime': order_obj.plannedtime,
                'pmplannergrp': order_obj.pmplannergrp,
                'inspectionlot': order_obj.inspectionlot,
                'instructions': order_obj.instructions,
                'extension': order_obj.extension,
            }

        processed_orders.append(order_i)

    

    return JsonResponse({'orders': processed_orders, 'total_pages': total_pages})




 





def equipments_load(request):

    filters = {} 

    field_mapping = {
    'inventorynr',
    'nomenclature',
    'modelnumber',
    'manufactserialnr',
    'inventoryref',
    'functlocation',
    }

    for field in field_mapping:
        value = request.GET.get(field)
        if field in {'inventorynr', 'nomenclature', 'modelnumber', 'manufactserialnr', 'inventoryref','functlocation'}:
                filters[f"{field}__icontains"] = value
        

    sorting_parameter = request.GET.get('sort', 'functlocation')
    sortequipment = request.GET.get('sortequipment', 'asc')

    if sortequipment == 'desc':
            sorting_parameter = '-' + sorting_parameter 


    equipments = equipment.objects.filter(**filters).order_by(        
            sorting_parameter ,'functlocation', 'nomenclature') 
    items_per_page = 150 
    paginator = Paginator(equipments, items_per_page)


    page = request.GET.get('page', 1)  # Get the requested page number

    try:
        equipments_page = paginator.page(page)
    except PageNotAnInteger:
        equipments_page = paginator.page(1)
    except EmptyPage:
        equipments_page = paginator.page(paginator.num_pages)

    # Process equipments for the current page
    processed_equipments = []
    total_pages = paginator.num_pages

    # Iterate through the equipments and include information
    for equipment_obj in equipments_page:
        equipment_i = {
            'id': equipment_obj.id,
            'inventorynr': equipment_obj.inventorynr,
            'nomenclature': equipment_obj.nomenclature,
            'modelnumber': equipment_obj.modelnumber,
            'manufactserialnr': equipment_obj.manufactserialnr,
            'inventoryref': equipment_obj.inventoryref,
            'functlocation': equipment_obj.functlocation[0] if equipment_obj.functlocation else None
        }

        processed_equipments.append(equipment_i)

    return JsonResponse({'equipments': processed_equipments, 'total_pages': total_pages})












def process_equipment(readequipment, readfunctlocation, readnomenclature, readmodelnumber, readmanufactserialnr, readinventoryref):
    try:
        existing_equipment = equipment.objects.get(inventorynr=readequipment)

        last_functlocation = existing_equipment.functlocation[-1] if existing_equipment.functlocation else None
        if last_functlocation == readfunctlocation:
            return existing_equipment
        else:
            existing_equipment.functlocation.append(readfunctlocation)
            existing_equipment.save()
            return existing_equipment

    except equipment.DoesNotExist:
        new_equipment = equipment(
            inventorynr=readequipment,
            nomenclature=readnomenclature,
            modelnumber=readmodelnumber,
            manufactserialnr=readmanufactserialnr,
            inventoryref=readinventoryref,
            functlocation=[readfunctlocation]  # Initialize functlocation as a list
        )
        new_equipment.save()
        return new_equipment
    



def order_import(request):
    if request.method == 'POST':    

        files = request.FILES.getlist('files[]')
        week_i = request.POST.get('week')
        personorderd_i = request.POST.get('personid')
        grouporderd_i =  request.POST.get('group')

        for index, file in enumerate(files):
            if file.content_type == 'application/pdf':
                
                try:




                        docinfo_i, issuer_i, blocks_i = open_pdf(file)
                        header_i=extract_maintenance_header(blocks_i)
                        instructions_i,extension_i=extract_maintenance_procedures(blocks_i)
                        order_i,ordertype_i,startdate_i,enddate_i,functlocation_i,equipment_i,modelnumber_i,manufactserialnr_i,inventorynr_i,plannedtime_i,pmplannergrp_i,inspectionlot_i=header_seperator(header_i)
                        readweek =  datetime.strptime(startdate_i, "%Y-%m-%d").isocalendar()[1]
                        readgroup = functlocation_i.split('.')[2].lstrip('0')
                        readequipment=equipment_i.split(' ')[0]
                        readnomenclature=equipment_i.split(' ')[1]
                        readmodelnumber=modelnumber_i
                        readmanufactserialnr=manufactserialnr_i
                        readinventoryref=inventorynr_i
                        readfunctlocation=functlocation_i.split(' ')[0]

                        group_instance, _ = group.objects.get_or_create(groupid=readgroup, defaults={'description': ""})
                        group_id = group_instance.id
                        equipment = process_equipment(readequipment, readfunctlocation, readnomenclature, readmodelnumber, readmanufactserialnr, readinventoryref)
                        
                        
                        
                        


                        new_order =   order(
                                                docinfo=docinfo_i,
                                                status=False,
                                                issuer=issuer_i,
                                                orderref=order_i,
                                                personorderd=personorderd_i if personorderd_i else 0 ,
                                                grouporderd=grouporderd_i if grouporderd_i else group_id,
                                                week=week_i if week_i else readweek,
                                                ordertype=ordertype_i,
                                                startdate=startdate_i,
                                                enddate=enddate_i,
                                                equipment=equipment,
                                                plannedtime= plannedtime_i,
                                                pmplannergrp=pmplannergrp_i,
                                                inspectionlot=inspectionlot_i,
                                                instructions=instructions_i,
                                                extension=extension_i,
                                            )
                        

                        new_order.save() 




            
                except Exception as e:
                        print(f"Exception occurred: {e}")
                

        return JsonResponse({'message': 'Files uploaded successfully.'})
    return JsonResponse({'message': 'Invalid request method.'})







def equipment_ohr_print(request):

            
    equipementId = request.GET.get('equipementId')
    
    if equipementId is None:
        return JsonResponse({'error': 'equipementInvnr parameter is required'}, status=400)
    
    
    
    equipement = get_object_or_404(equipment, id=equipementId)
    
    equipement_data = {
        'inventorynr': equipement.inventorynr,
        'nomenclature': equipement.nomenclature,
        'modelnumber': equipement.modelnumber,
        'manufactserialnr': equipement.manufactserialnr,
        'inventoryref': equipement.inventoryref,
        'functlocation': equipement.functlocation,
    }


    orders = list(order.objects.filter(equipment=equipementId).values('instructions', 'submitdate'))


    create_ohr(orders)



    return JsonResponse({'equipement': "RESPONSE TEMP"})







def order_post(request): 
    user = request.user
    if request.method == 'POST':
        submission = json.loads(request.body)
        orderId = submission.get('orderId')
        orderRef = submission.get('orderRef')
        formData = submission.get('formData')
        extData = submission.get('extData')
        formextData = submission.get('formextData')
        formextanmlsData = submission.get('formextanmlsData')
        formextnoteData = submission.get('formextnoteData')



        try:
            instance = order.objects.get(id=orderId)
            manipulated_instructions=instance.instructions
            for idxg in range(len(formData)):
                
                if manipulated_instructions[idxg]['procedure_type']==2 and formData[idxg]['type']==2:  
                    manipulated_instructions[idxg]['procedure_instructions']=formData[idxg]['value']
                elif manipulated_instructions[idxg]['procedure_type']==3 and formData[idxg]['type']==3:
                    for idxl in range(len(formData[idxg]['value'])):
                        manipulated_instructions[idxg]['procedure_instructions'][idxl]['status']=formData[idxg]['value'][idxl]

            instance.instructions=manipulated_instructions
            if extData != "NONE":
                instance.extension['extension_instructions']=formextData
                instance.extension['extension_anomalies']=formextanmlsData
                instance.extension['extension_note']=formextnoteData
            instance.status = True
            instance.personorderd=user.id
            instance.submitdate=timezone.now().date()

            instance.save()
            

            return JsonResponse({'success': True, 'url': '/'})

        except order.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'order not found.'})

        return JsonResponse({'success': True, 'url': '/'})
    
    return JsonResponse({'success': False, 'message': 'invalid request method'})


def is_valid_pdf(pdf_data):
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
        # Additional validation checks here, if needed
        return True
    except PyPDF2.PdfReadError:
        return False






def order_print(request, order_id):


    order_obj = order.objects.select_related('equipment').filter(id=order_id).first()
    order_i = {
            'id': order_obj.id,
            'docinfo': order_obj.docinfo,
            'status': order_obj.status,
            'issuer': order_obj.issuer,
            'orderref': order_obj.orderref,
            'personorderd': order_obj.personorderd,
            'grouporderd': order_obj.grouporderd,
            'week': order_obj.week,
            'ordertype': order_obj.ordertype,
            'startdate': order_obj.startdate.strftime('%Y-%m-%d') if order_obj.startdate else None,
            'enddate': order_obj.enddate.strftime('%Y-%m-%d') if order_obj.enddate else None,
            'submitdate': order_obj.submitdate.strftime('%Y-%m-%d') if order_obj.submitdate else None,
            'equipment': {
                'inventorynr': order_obj.equipment.inventorynr,
                'nomenclature': order_obj.equipment.nomenclature,
                'modelnumber': order_obj.equipment.modelnumber,
                'manufactserialnr': order_obj.equipment.manufactserialnr,
                'inventoryref': order_obj.equipment.inventoryref,
                'functlocation': order_obj.equipment.functlocation[-1] if order_obj.equipment.functlocation else None
            },
            'plannedtime': order_obj.plannedtime,
            'pmplannergrp': order_obj.pmplannergrp,
            'inspectionlot': order_obj.inspectionlot,
            'instructions': order_obj.instructions,
            'extension': order_obj.extension,
        }
    


    
    user_profile = userprofile.objects.get(user=order_obj.personorderd)

    if user_profile:
        order_i['personorderd'] = f"{user_profile.lname} {user_profile.fname}"
    else:
        order_i['personorderd'] = None



    pdf_data = create_pdf(order_i)




    response = HttpResponse(pdf_data, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="order.pdf"'
    

    response.write(pdf_data)

    return response



























def ulogin(request):
    error_message = None
    next_url = request.GET.get('next')  # Get the value of 'next' from the query parameters

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if next_url:  # If 'next' exists, redirect to the provided URL
                return redirect(next_url)
            else:
                return redirect('index')
        else:
            error_message = "Nom d'utilisateur ou mot de passe invalide."

    return render(request, 'apgmp/login.html', {'error_message': error_message})



@login_required
def ulogout(request):
    logout(request)
    return redirect('index')


@login_required
def user_create(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        fname = request.POST.get('fname')
        lname = request.POST.get('lname')
        role = request.POST.get('role')
        group = request.POST.getlist('group')
        
        try:
            # Check if any required field is empty
            if not (username and password and fname and lname and role):
                raise ValueError("Tous les champs sont obligatoires.")
            
            # Create user and profile
            user = User.objects.create_user(username=username, password=password)
            is_issuer = role == 'Organisateur'
            profile = userprofile.objects.create(user=user, fname=fname, lname=lname, is_issuer=is_issuer)
            
            if group:
                profile.group = group
                profile.save()
            
            return redirect('adminupanel')
        except IntegrityError:
            messages.error(request, "Ce profil existe déjà.")
        except ValueError as e:
            messages.error(request, str(e))

    return render(request, 'apgmp/user_create.html')




@login_required
def group_load(request): 
    groups = group.objects.all()
    groups = [{'id': group.id, 'groupid': group.groupid} for group in groups]
    return JsonResponse({'groups': groups})




@login_required
def user_edit(request, username):
    return render(request, 'apgmp/user_edit.html', {'username': username})




@login_required
def user_update(request, username):
    if request.method == 'POST':
        try:
            user_profile = get_object_or_404(userprofile, user__username=username)
            user = user_profile.user

            lname = request.POST.get('lname')
            fname = request.POST.get('fname')
            role = request.POST.get('role')
            group = request.POST.get('group')
            password = request.POST.get('password')
            user_profile.fname = fname
            user_profile.lname = lname
            user_profile.is_issuer = role == 'Organisateur'
            if role != 'Organisateur':
                user_profile.group = group
            user_profile.save()
            if password:
                user.set_password(password)
                user.save()
            


            messages.success(request, 'User updated successfully.')
            return redirect('/adminupanel/')  # Redirect to the specified URL
        except Exception as e:
            messages.error(request, str(e))
            return redirect('user_edit', username=username)  # Redirect back to the edit page with an error message
    else:

        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    






@login_required
def user_delete(request, username):
    if request.method == 'POST':
        user_profile = get_object_or_404(userprofile, user__username=username)
        user = user_profile.user
        user.delete()
        return JsonResponse({'success': True, 'redirect': '/adminupanel/'})
    else:
        return JsonResponse({'success': False, 'message': 'Invalid request method'})







def users_load(request):
    filters = {}
    field_mapping = {
        'username',
        'is_issuer',
        'group',
    }

    for field in field_mapping:
        value = request.GET.get(field)
        if value is not None and value != '':
            filters[field] = value

    if filters:
        tempUsers = User.objects.filter(Q(**filters) & Q(userprofile__isnull=False))
    else:
        tempUsers = User.objects.filter(userprofile__isnull=False)

    name_filter = request.GET.get('name')
    if name_filter is not None and name_filter != '':
        tempUsers = tempUsers.annotate(full_name=Concat('userprofile__fname', Value(' '), 'userprofile__lname', output_field=CharField()))
        tempUsers = tempUsers.filter(full_name__icontains=name_filter)
    
    users = []

    for user in tempUsers:
        users.append({
            'username': user.username,
            'fname': user.userprofile.fname,
            'lname': user.userprofile.lname,
            'is_issuer': user.userprofile.is_issuer,
        })

    return JsonResponse({'users': users})



def user_load(request): 
    reg_num = request.GET.get('regNum')
    if reg_num:
        try:
            user = User.objects.get(username=reg_num)
            profile = user.userprofile  # Access the related userprofile
            instuser = {
                    'username': user.username,
                    'fname': profile.fname,
                    'lname': profile.lname,
                    'group': profile.group,
                    'is_issuer': profile.is_issuer,
            }


            return JsonResponse({'user': instuser})
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'})
    else:
        return JsonResponse({'error': 'No username provided'})
    


