package payment;

import com.intuit.karate.junit5.Karate;

class PaymentChargeRunner {

    @Karate.Test
    Karate testPaymentCharge() {
        return Karate.run("payment-charge").relativeTo(getClass());
    }
}

