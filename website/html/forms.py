"""
<Program Name>
  forms.py

<Started>
  October, 2008

<Author>
  Ivan Beschastnikh
  ivan@cs.washington.edu
  
  Jason Chen
  jchen@cs.washington.edu
<Purpose>

<Usage>
  For more information on forms in django see:
  http://docs.djangoproject.com/en/dev/topics/forms/
"""

from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
import django.forms as forms

from seattlegeni.common.exceptions import *
from seattlegeni.common.util import validations
from seattlegeni.website.control import interface

MAX_PUBKEY_UPLOAD_SIZE = 2048

class PubKeyField(forms.FileField):
  def clean(self,value,initial):
    forms.FileField.clean(self,value,initial)
    if value is None:
      return None
    if value.size > MAX_PUBKEY_UPLOAD_SIZE:
      raise forms.ValidationError, "Public key too large, file size limit is " + str(MAX_PUBKEY_UPLOAD_SIZE) + " bytes"
    # get the pubkey out of the uploaded file
    pubkey = value.read()
    try:
      validations.validate_pubkey_string(pubkey)
    except ValidationError, err:
      raise forms.ValidationError, str(err)
    return pubkey



class GeniUserCreationForm(DjangoUserCreationForm):
  affiliation = forms.CharField(error_messages={'required': 'Enter an Affiliation'})
  email = forms.CharField(label="E-mail Address", error_messages={'required': 'Enter an E-mail Address'})
  pubkey = PubKeyField(label="My Public Key", required=False)
  gen_upload_choice = forms.ChoiceField(label="", choices=((1, 'Generate key pairs for me'), (2, 'Let me upload my public key')))
  username = forms.CharField(label="Username", error_messages={'required': 'Enter a username'}, max_length=validations.USERNAME_MAX_LENGTH)
  
  def __init__(self, *args):
    DjangoUserCreationForm.__init__(self, *args)
    #self.fields['username'].error_messages['required'] = 'Enter a username'
    self.fields['password1'].error_messages['required'] = 'Enter a password'
    self.fields['password2'].error_messages['required'] = 'Verify your password'

  def clean_username(self):
    value = self.cleaned_data['username']
    try:
      validations.validate_username(value)
    except ValidationError, err:
      raise forms.ValidationError, str(err)
    return value
  
  def clean_password1(self):
    value = self.cleaned_data['password1']
    try:
      validations.validate_password(value)
    except ValidationError, err:
      raise forms.ValidationError, str(err)
    return value
  
  def clean_affiliation(self):
    value = self.cleaned_data['affiliation']
    try:
      validations.validate_affiliation(value)
    except ValidationError, err:
      raise forms.ValidationError, str(err)
    return value
  
  def clean_email(self):
    value = self.cleaned_data['email']
    try:
      validations.validate_email(value)
    except ValidationError, err:
      raise forms.ValidationError, str(err)
    return value



def gen_get_form(geni_user, req_post=None):
  """
  <Purpose>
      Dynamically generates a GetVesselsForm that has the right
      number vessels (the allowed number of vessels a user may
      acquire). Possibly generate a GetVesselsForm from an HTTP POST
      request.

  <Arguments>
      geni_user:
          geni_user object
      req_post:
          An HTTP POST request (django) object from which a
          GetVesselsForm may be instantiated. If this argument is
          not supplied, a blank form will be created

  <Exceptions>
      None.

  <Side Effects>
      None.

  <Returns>
      A GetVesselsForm object that is instantiated with a req_post
      (if given). None is returned if the user cannot acquire any
      more vessels.
  """
      
  # the total number of vessels a user may acquire
  #TODO: Interface call that gets remaining vessel credit.
  #max_num = geni_user.vessel_credit_remaining()
  total_vessel_credits = interface.get_total_vessel_credits(geni_user)
  num_acquired_vessels = len(interface.get_acquired_vessels(geni_user))
  avail_vessel_credits = total_vessel_credits - num_acquired_vessels
  
  # JTC: Dynamic generation of available vessel amounts based off of avail_vessel_credits
  step = range(1, 10, 1)
  if avail_vessel_credits < 20:
    step = range(1, avail_vessel_credits+1, 1)
  elif avail_vessel_credits >= 20 and avail_vessel_credits < 100:
    step.extend(range(10, avail_vessel_credits+1, 10))
  elif avail_vessel_credits >= 100:
    step.extend(range(10, 100, 10))
    step.extend(range(100, avail_vessel_credits+1, 100))
  try:
    existdup = step.index(avail_vessel_credits)
  except ValueError:
    step.extend([avail_vessel_credits])
  
  # don't return this form if user has no more available vessel credits
  if avail_vessel_credits == 0:
    return None

  # dynamically generate the get vessels form
  #get_vessel_choices = zip(range(1,max_num+1),range(1,max_num+1))
  get_vessel_choices = zip(step, step)
  
  class GetVesselsForm(forms.Form):
    """
    <Purpose>
        Generates a form to acquire vessels by the user
    <Side Effects>
        None
    <Example Use>
        GetVesselsForm()
            to generate a blank form
        GetVesselsForm(post_request)
            to generate a form from an existing POST request
    """
    # maximum number of vessels a user is allowed to acquire
    #num = forms.ChoiceField(choices=get_vessel_choices, error_messages={'required' : 'Please enter the number of vessels to acquire'})
    num = forms.ChoiceField(choices=get_vessel_choices)
    
    # the various environment types the user may select from
    #env = forms.ChoiceField(choices=((1,'LAN'),(2,'WAN'),(3,'Random')), error_messages={'required' : 'Please enter the networking environment for vessels to acquire'})
    env = forms.ChoiceField(choices=(('wan','WAN'),('lan','LAN'),('nat','NAT'),('rand','Random')))
    
    def clean_num(self):
      value = int(self.cleaned_data['num'])
      if value < 1:
        raise forms.ValidationError("Invalid vessel number selection.")
      return value
    
    def clean_env(self):
      value = str(self.cleaned_data['env'])
      if not (value == 'wan' or value == 'lan' or value == 'nat' or value == 'rand'):
        raise forms.ValidationError("Invalid vessel type selection.")
      return value
    
    def get_errors_as_str(self):
      return str(self.errors)
  
  if req_post is None:
      return GetVesselsForm()
  return GetVesselsForm(req_post)
