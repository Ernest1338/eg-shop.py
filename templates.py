from web import Template, read_file

template = {
    "base": Template("templates/base.html"),
    "index": Template("templates/index.html"),
    "login-page": Template("templates/login.html"),
    "register-page": Template("templates/register.html"),
    "listing": Template("templates/listing.html"),
    "listing-page": Template("templates/listing-page.html"),
    "shopping-cart": Template("templates/shopping-cart.html"),
    "shopping-cart-item": Template("templates/shopping-cart-item.html"),
    "add-to-cart-button": Template("templates/add-to-cart-button.html"),
    "delete-from-cart-button": Template("templates/delete-from-cart-button.html"),
    "checkout-widget": Template("templates/checkout-widget.html"),
    "profile": Template("templates/profile.html"),
    "transaction": Template("templates/transaction.html"),
    "transaction-page": Template("templates/transaction-page.html"),
    "bank": Template("templates/bank.html"),
}

cache = {
    "login": template["login-page"].render({"info": ""}),
    "register": template["register-page"].render({"info": ""}),
    "navbar": read_file("templates/navbar.html"),
    "navbar-logged": read_file("templates/navbar-logged.html"),
    "change-pass": read_file("templates/change-pass.html"),
}
