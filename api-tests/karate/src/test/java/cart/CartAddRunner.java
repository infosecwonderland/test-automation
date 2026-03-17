package cart;

import com.intuit.karate.junit5.Karate;

class CartAddRunner {

    @Karate.Test
    Karate testCartAdd() {
        return Karate.run("cart-add").relativeTo(getClass());
    }
}

