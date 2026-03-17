package order;

import com.intuit.karate.junit5.Karate;

class OrderCreateRunner {

    @Karate.Test
    Karate testOrderCreate() {
        return Karate.run("order-create").relativeTo(getClass());
    }
}

