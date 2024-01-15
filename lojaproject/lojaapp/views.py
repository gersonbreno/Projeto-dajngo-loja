from typing import Any
from django.forms.models import BaseModelForm
from django.http import HttpRequest, HttpResponse, HttpResponse as HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import View, TemplateView, CreateView, FormView
from django.urls import reverse_lazy
from .forms import ChegarPedidoForms, ClienteRegistrarForms, ClienteEntrarForm
from.models import *
from django.contrib.auth import authenticate, login, logout


class LojaMixin(object):
    def dispatch(self, request, *args, **kwargs):
        carro_id = request.session.get("carro_id")
        if carro_id:
            carro_obj = Carro.objects.get(id=carro_id)
            if request.user.is_authenticated and hasattr(request.user, 'cliente'):
                carro_obj.cliente = request.user.cliente
                carro_obj.save()
        return super().dispatch(request, *args, **kwargs)
    


class HomeView(LojaMixin, TemplateView):
    template_name = 'home.html'
    def get_context_data(self, **kwargs ):
        context = super().get_context_data(**kwargs)
        context['produto_list'] = Produto.objects.all().order_by('-id')
        return context
        
       


class SobreView(TemplateView):
    template_name = 'sobre.html'

class ContatoView(TemplateView):
    template_name = 'contato.html'
    
class TodosProdutosView(LojaMixin,TemplateView):
    template_name = 'todosprodutos.html'
    def get_context_data(self, **kwargs ):
        context = super().get_context_data(**kwargs)
        context['todosctegorias'] = Categoria.objects.all()
        return context
  
class ProdutoDetalheView(LojaMixin, TemplateView):
    template_name = 'produtodetalher.html'
    def get_context_data(self, **kwargs ):
        context = super().get_context_data(**kwargs)
        url_slug = self.kwargs['slug']
        produto = Produto.objects.get(slug=url_slug) 
        produto.visualizacao += 1
        produto.save()
        context['produto'] = produto
        return context
    
  

  
class AddCarroView(LojaMixin,TemplateView):
    template_name = 'addprocarro.html'
    def get_context_data(self, **kwargs ):
        context = super().get_context_data(**kwargs)
        produto_id = self.kwargs['pro_id']
        produto_obj = Produto.objects.get(id=produto_id) 
        carro_id = self.request.session.get("carro_id", None)
        if carro_id:
            carro_obj = Carro.objects.get(id=carro_id)
            produto_no_carro = carro_obj.carroproduto_set.filter(produto= produto_obj)
            if produto_no_carro.exists():
                carroproduto = produto_no_carro.last()
                carroproduto.quantidade += 1
                carroproduto.quantidade += produto_obj.venda
                carroproduto.save()
                carro_obj.total += produto_obj.venda
                carro_obj.save()
            else:
                carroproduto = CarroProduto.objects.create(carro =carro_obj,produto = produto_obj,avaliacao = produto_obj.venda,quantidade = 1, subtotal =  produto_obj.venda)
                carro_obj.total += produto_obj.venda
                carro_obj.save()    
        else:
            carro_obj = Carro.objects.create(total = 0)
            self.request.session['carro_id'] = carro_obj.id
            carroproduto = CarroProduto.objects.create(carro =carro_obj,produto = produto_obj,avaliacao = produto_obj.venda,quantidade = 1, subtotal =  produto_obj.venda)
            carro_obj.total += produto_obj.venda
            carro_obj.save()
        return context
    
   
class  MeuCarroView(LojaMixin,TemplateView):
    template_name = 'meucarro.html'
    def get_context_data(self, **kwargs ):
        context = super().get_context_data(**kwargs)
        carro_id = self.request.session.get("carro_id", None)
        if carro_id:
            carro = Carro.objects.get(id=carro_id)
        else:
            carro = None
        context['carro'] = carro
        return context

            
   
class  ManipularCarroView(View):
    def get(self,request, *args, **kwargs ):
        cp_id = self.kwargs["cp_id"]
        acao = request.GET.get("acao")
        cp_obj = CarroProduto.objects.get(id=cp_id)
        carro_obj = cp_obj.carro
        
        if acao == "inc":
            cp_obj.quantidade += 1
            cp_obj.subtotal += cp_obj.avaliacao
            cp_obj.save()
            carro_obj.total += cp_obj.avaliacao
            carro_obj.save()
        elif acao == "dcr":
            cp_obj.quantidade -= 1
            cp_obj.subtotal -= cp_obj.avaliacao
            cp_obj.save()
            carro_obj.total -= cp_obj.avaliacao
            carro_obj.save()
            if cp_obj.quantidade == 0:
                cp_obj.delete()

        elif acao == "rmv":
            carro_obj.total -= cp_obj.subtotal
            carro_obj.save()
            cp_obj.delete()
        else:
            pass
        return redirect("lojaapp:meucarro")
    


class  LimparCarroView(View):
    def get(self,request, *args, **kwargs ):
        carro_id = request.session.get("carro_id", None)
        if carro_id:
            carro = Carro.objects.get(id = carro_id)
            carro.carroproduto_set.all().delete()
            carro.total = 0
            carro.save()

        return redirect("lojaapp:meucarro")

class  CheckoutView(CreateView):
    template_name = 'processar.html'
    form_class = ChegarPedidoForms
    success_url = reverse_lazy("lojaapp:home")
    
    def dispatch(self, request,*args, **kwargs):
        if request.user.is_authenticated and request.user.cliente:
            pass
        else:
            return redirect("/entrar/?next=/checkout/")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs ):
        context = super().get_context_data(**kwargs)
        carro_id = self.request.session.get("carro_id", None)
        if carro_id:
            carro_obj = Carro.objects.get(id=carro_id)
        else:
            carro_obj = None
        context['carro'] = carro_obj
        return context
    

    def form_valid(self, form):
        carro_id = self.request.session.get("carro_id")
        if carro_id:
            carro_obj = Carro.objects.get(id = carro_id)
            form.instance.carro = carro_obj
            form.instance.subtotal = carro_obj.total
            form.instance.desconto = 0
            form.instance.total  = carro_obj.total
            form.instance.pedido_status = "Pedido  Recebido"
            del self.request.session['carro_id']
        else:
            return redirect("lojaapp:home")
        return super().form_valid(form)



     
 
class  ClienteResgistrarView(CreateView):
    template_name = 'registrarcliente.html'
    form_class = ClienteRegistrarForms
    success_url = reverse_lazy("lojaapp:home")
    
    def form_valid(self, form):
        username = form.cleaned_data.get("username")
        password = form.cleaned_data.get("password")
        email = form.cleaned_data.get("email")
        user = User.objects.create_user(username,email,password)
        form.instance.user = user
        login(self.request, user)
        return super().form_valid(form)
    
    def get_success_url(self):
        if "next" in self.request.GET:
            next_url = self.request.GET.get("next")
            return next_url
        else:
            return self.success_url
class ClienteSairView(View):
    def get(self, request):
        logout(request)
        return redirect("lojaapp:home")
    
 
class ClienteentrarView(FormView):
    template_name = 'Clienteentrar.html'
    form_class = ClienteEntrarForm
    success_url = reverse_lazy("lojaapp:home")
    def form_valid(self, form):
        unome = form.cleaned_data.get("username")
        pword = form.cleaned_data.get("password")
        user = authenticate(username= unome, password = pword)
        if user is not None and user.cliente:
            login(self.request, user)
        else:
            return render(self.request, self.template_name, {"form": self.form_class, "error": "Senha e usuario Invalido Tente Novamente!"})

        return super().form_valid(form)
    
    def get_success_url(self):
        if "next" in self.request.GET:
            next_url = self.request.GET.get("next")
            return next_url
        else:
            return self.success_url
    # def form_valid(self, form):
    #     # Extract username and password from the form
    #     username = form.cleaned_data.get("username")
    #     password = form.cleaned_data.get("password")

    #     # Check if username and password are provided
    #     if not username or not password:
    #         return render(
    #             self.request,
    #             self.template_name,
    #             {"form": form, "error": "Informe usuário e senha."}
    #         )

    #     # Authenticate the user
    #     usr = authenticate(username=username, password=password)

    #     # Check if authentication was successful and if the user has a related Cliente
    #     if usr is not None and hasattr(usr, 'cliente'):
    #         # Login the user
    #         login(self.request, usr)
    #         return super().form_valid(form)  # Continue with the default behavior

    #     # If authentication failed or user doesn't have a related Cliente, render an error
    #     return render(
    #         self.request,
    #         self.template_name,
    #         {"form": form, "error": "Senha e usuário inválidos. Tente novamente!"}
    #     )

    # def get_success_url(self):
    #     # Customize the success URL if needed
    #     return self.success_url
        
class ClientePerfilView(TemplateView):
     template_name = 'Clienteperfil.html'
     def dispatch(self, request,*args, **kwargs):
        if request.user.is_authenticated and request.user.cliente:
            pass
        else:
            return redirect("/entrar/?next=/perfil/")

        return super().dispatch(request, *args, **kwargs)
     def get_context_data(self, **kwargs ):
        context = super().get_context_data(**kwargs)
        cliente = self.request.user.cliente
        context['cliente']= cliente

        pedido = Pedido_order.objects.filter(carro__cliente = cliente)
        context['pedido'] = pedido
        return context
    