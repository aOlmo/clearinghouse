"""
<Program Name>
  accounts/forms.py

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

class PubKeyField(forms.FileField):
  def clean(self,value,initial):
    forms.FileField.clean(self,value,initial)
    if value is None:
      return None
    if value.size > 2048:
      raise forms.ValidationError, "Public key too large, file size limit is 2048 bytes"
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
  #pubkey = forms.FileField(label="My Public Key", required=False)
  pubkey = PubKeyField(label="My Public Key", required=False)
  gen_upload_choice = forms.ChoiceField(label="", choices=((1, 'Generate key pairs for me'), (2, 'Let me upload my public key')))

  def __init__(self, *args):
    DjangoUserCreationForm.__init__(self, *args)
    self.fields['username'].error_messages['required'] = 'Enter a username'
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
  