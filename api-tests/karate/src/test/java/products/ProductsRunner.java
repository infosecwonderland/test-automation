package products;

import com.intuit.karate.junit5.Karate;

class ProductsRunner {

    @Karate.Test
    Karate testProducts() {
        return Karate.run("products").relativeTo(getClass());
    }
}

