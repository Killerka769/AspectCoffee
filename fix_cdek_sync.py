import os

path = '/app/apps/orders/templates/orders/basket.html'
with open(path, 'r') as f:
    content = f.read()

# Fix cdekSelectCity to also update the form city field
old = """            async cdekSelectCity(city) {
                this.cdekSelectedCity = city;
                this.cdekCityQuery = city.city + (city.region && city.region !== city.city ? ', ' + city.region : '');
                this.cdekCities = [];
                this.selectedPvz = null;
                this.cdekDeliveryCost = null;
                this.cdekOfficeFilter = '';
                if (this.deliveryType === 'cdek_pvz') {
                    await this.cdekLoadOffices();
                }
                await this.cdekCalcCost();
            },"""

new = """            async cdekSelectCity(city) {
                this.cdekSelectedCity = city;
                this.cdekCityQuery = city.city + (city.region && city.region !== city.city ? ', ' + city.region : '');
                this.cdekCities = [];
                this.selectedPvz = null;
                this.cdekDeliveryCost = null;
                this.cdekOfficeFilter = '';
                const cityFullName = city.city + (city.region && city.region !== city.city ? ', ' + city.region : '');
                document.querySelectorAll('input[name=city], input[name=city_m]').forEach(function(el) { el.value = cityFullName; });
                if (this.deliveryType === 'cdek_pvz') {
                    await this.cdekLoadOffices();
                }
                await this.cdekCalcCost();
            },"""

if old in content:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("OK - CDEK city sync: now updates form city field on selection")
else:
    print("ERROR: cdekSelectCity block not found")

print("Done")
