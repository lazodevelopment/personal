const functions = require('firebase-functions/v1');
const admin = require('firebase-admin');
const axios = require('axios');
const sgMail = require('@sendgrid/mail');

// Initialize Firebase Admin (only once)
admin.initializeApp();

const firestore = admin.firestore();

// ============================================
// CONFIGURATION
// ============================================

// PayArc API Configuration
const PAYARC_API_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImZiODEzODMzZDVkMzc4ZjU4NDUxYjhiYzk5MTRjMTg5In0.eyJhdWQiOiIyMzcxMiIsImp0aSI6ImU4NjYxMTExMzk3ODNlODYyY2I1MTQ1NDlkN2EyY2U1ZmZjNWI1NGUyMGJmMDBmZTE1MjkyMGRhNzc3YWJmNzgyNjg5YzZhZTc3NDAyNTM2IiwiaWF0IjoxNzU5ODQ3MDIzLCJuYmYiOjE3NTk4NDcwMjMsImV4cCI6MTkxNzUyNzAyMywic3ViIjoiNTI2MjEiLCJzY29wZXMiOiIqIn0.XkV0DMV-XOGhrMmjSEXfngPzkgApnIcJ-hs-mUlrgxbNt3l-EGL9XokaC1iK0C_EHMXFT5UEsLLfhrVuu7GtvqOpdxe7AnEUkR-M_Sm05PS9BQ4-qVWIt3dfyDlXDoZNeulY3g2fF44DMn7fUbFtvU1vrt3-zM9HTfssWGFwPdTCRLnoLY8bo9BUgdlg5VSyF4tFrkELqa4vS26omYsdnnqac04opVVJlF5VpbU8fSF0jfQJItX-Wv2F-LZkGTA-9f_waYHxHVHSPBgkeoZSj0Is1zuHupnCHdtOw34dQ7jPTTZ20hwJEw1Ly_Ue1QiovI2cr_zYLl_Kqi6eWJ6okzZpXsFI9G6xatfCsmf8aTY5lZnNU-NxevaUDJl7T7JrrHb1LljR6AXa3Qkq9nupMQGOeJ5hk09uPFxSqAM5avQ-A2Hb8iaze78yAo1UbAFGfhrt-eXLr8F3qqer_Chdl779f4P4WZCGE8mG0fPdrnVHxrTYNpmQiKSwR4Bo6cD0Gxb23dmKGVmjrD98G1IyAL8taWdBzpc0kvGYlH-a7R6zX_d3M9cLJpvAb-sBRTtlaTqjzB7yCurC8RL-0K2b9XWRaZZ2t0FC3ee3Eup_qFuu1WSptRtgQW53ArpN4smCFOmfmcrrnJpCl1rQqS7MEYLF6dRxOYlEugEPDmge1IE';
const PAYARC_API_URL = 'https://api.payarc.net/v1';

// Test card numbers that should always use test mode
const TEST_CARDS = ['4242424242424242', '4111111111111111', '5555555555554444'];

// Push Notifications Configuration
const kFcmTokensCollection = 'fcm_tokens';
const kPushNotificationsCollection = 'ff_push_notifications';
const kSchedulerIntervalMinutes = 60;


// ============================================
// PAYMENT PROCESSING FUNCTIONS
// ============================================

// Main payment processing function
exports.processMembershipPayment = functions.https.onCall(async (data, context) => {
  console.log('=== Payment Request Received ===');
  console.log('Timestamp:', new Date().toISOString());
  
  // Log received data safely
  try {
    const dataKeys = data ? Object.keys(data) : [];
    console.log('Data keys received:', dataKeys);
    
    if (data) {
      console.log('Payment details received for:', data.email || 'unknown');
      console.log('Amount:', data.amount);
      console.log('Card last 4:', data.cardNumber ? data.cardNumber.slice(-4) : 'N/A');
      console.log('User ID from context:', context.auth?.uid || 'anonymous');
    }
  } catch (logError) {
    console.log('Error logging data:', logError.message);
  }
  
  // Extract payment data - handle different request structures
  let actualData = {};
  
  if (data && typeof data === 'object') {
    if (data.data && typeof data.data === 'object') {
      actualData = data.data;
    } else {
      actualData = data;
    }
  }
  
  console.log('Extracted actualData:', Object.keys(actualData));
  
  const { 
    amount, 
    cardNumber, 
    expiry, 
    cvv, 
    firstName, 
    lastName, 
    email, 
    phone,
    birthdate,
    subscriptionType,
    userId,
    billing_address,
    city,
    state,
    zip,
    country
  } = actualData;
  
  console.log('Extracted values:', {
    amount,
    cardNumber: cardNumber ? `****${cardNumber.slice(-4)}` : 'missing',
    email: email || 'missing',
    firstName: firstName || 'missing',
    lastName: lastName || 'missing'
  });
  
  // Validate required fields
  if (!amount || !cardNumber || !expiry || !cvv || !email) {
    const missingFields = [];
    if (!amount) missingFields.push('amount');
    if (!cardNumber) missingFields.push('cardNumber');
    if (!expiry) missingFields.push('expiry');
    if (!cvv) missingFields.push('cvv');
    if (!email) missingFields.push('email');
    
    console.error('Missing required fields:', missingFields);
    throw new functions.https.HttpsError(
      'invalid-argument', 
      `Missing required fields: ${missingFields.join(', ')}`
    );
  }
  
  // Get or create user ID
  const finalUserId = context.auth?.uid || userId || `user_${Date.now()}`;
  console.log('Processing payment for user:', finalUserId);
  
  // Check if this is a test card
  const cleanCardNumber = cardNumber.replace(/\s/g, '');
  const isTestCard = TEST_CARDS.includes(cleanCardNumber);
  
  if (isTestCard) {
    console.log('Test card detected - using test mode');
  } else {
    console.log('Real card detected - processing with PayArc live API');
    console.log('Card type:', cleanCardNumber.startsWith('4') ? 'Visa' : 
                           cleanCardNumber.startsWith('5') ? 'Mastercard' : 
                           cleanCardNumber.startsWith('3') ? 'Amex' : 'Unknown');
  }
  
  let paymentResult;
  let paymentMode = 'live';
  let subscriptionId = null;
  
  try {
    if (isTestCard) {
      // Test mode for test cards
      console.log('Processing test payment...');
      paymentResult = {
        id: `test_${Date.now()}`,
        status: 'succeeded',
        amount: amount * 100,
        test_mode: true
      };
      paymentMode = 'test';
      subscriptionId = `test_sub_${Date.now()}`;
    } else {
      // Real PayArc payment processing
      console.log('Processing REAL PayArc payment...');
      console.log('PayArc API URL:', PAYARC_API_URL);
      console.log('Using token ending in:', PAYARC_API_TOKEN.slice(-10));
      
      // Parse expiry
      const [expMonth, expYear] = expiry.split('/');
      console.log('Parsed expiry - Month:', expMonth, 'Year:', expYear);
      
      // First, create or get customer
      let customerId;
      try {
        const userDoc = await firestore.collection('users').doc(finalUserId).get();
        const userData = userDoc.exists ? userDoc.data() : null;
        
        if (userData && userData.payarcCustomerId) {
          customerId = userData.payarcCustomerId;
          console.log('Using existing PayArc customer:', customerId);
        } else {
          console.log('Creating new PayArc customer...');
          
          let customerPhone = '';
          if (phone) {
            const cleanPhone = phone.replace(/\D/g, '');
            if (cleanPhone.length >= 10 && cleanPhone.length <= 11) {
              customerPhone = cleanPhone.length === 11 ? cleanPhone.slice(1) : cleanPhone;
            }
          }
          
          const customerData = {
            email: email,
            first_name: firstName || '',
            last_name: lastName || '',
            phone: customerPhone,
            description: `Kurv Health ${subscriptionType || 'individual'} member`
          };
          
          console.log('Customer data:', {
            ...customerData,
            phone: customerPhone ? `${customerPhone.slice(0,3)}***${customerPhone.slice(-4)}` : 'none'
          });
          
          const customerResponse = await axios.post(
            `${PAYARC_API_URL}/customers`,
            customerData,
            {
              headers: {
                'Authorization': `Bearer ${PAYARC_API_TOKEN}`,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
              }
            }
          );
          
          console.log('Customer creation response status:', customerResponse.status);
          console.log('Customer creation response:', JSON.stringify(customerResponse.data, null, 2));
          
          customerId = customerResponse.data.data.object_id || customerResponse.data.data.id;
          console.log('Created PayArc customer:', customerId);
        }
      } catch (customerError) {
        console.error('Customer creation error:', customerError.message);
        if (customerError.response) {
          console.error('Customer creation error response:', JSON.stringify(customerError.response.data, null, 2));
          console.error('Customer creation error status:', customerError.response.status);
        }
      }
      
      // Format phone number
      let payarcPhone = '';
      if (phone) {
        const cleanPhone = phone.replace(/\D/g, '');
        if (cleanPhone.length >= 10 && cleanPhone.length <= 11) {
          payarcPhone = cleanPhone.length === 11 ? cleanPhone.slice(1) : cleanPhone;
        }
      }
      
      console.log('Phone formatting:', {
        original: phone,
        cleaned: payarcPhone
      });
      
      // Create charge
      const chargeData = {
        currency: 'usd',
        amount: Math.round(amount * 100),
        card_number: cleanCardNumber,
        exp_month: expMonth.padStart(2, '0'),
        exp_year: expYear.length === 2 ? `20${expYear}` : expYear,
        cvv: cvv,
        statement_descriptor: 'Kurv Health',
        cardholder_name: `${firstName} ${lastName}`.trim(),
        capture: true,
        address_line_1: billing_address || '',
        address_line_2: '', 
        address_city: city || '',
        address_state: state || '',
        address_zip: zip || '',
        address_country: country || 'US',
        email: email,
        phone: payarcPhone,
        description: `Kurv Health ${subscriptionType || 'individual'} membership - Monthly`,
        source: 'card_not_present',
        avs_street_match: 'optional',
        avs_zip_match: 'optional',
        merchant_defined_field_1: 'kurv_health_subscription',
        merchant_defined_field_2: subscriptionType || 'individual',
        merchant_defined_field_3: finalUserId,
        recurring: true,
        metadata: JSON.stringify({
          userId: finalUserId,
          subscriptionType: subscriptionType || 'individual',
          recurring: 'monthly',
          source: 'kurv_health_app'
        })
      };
      
      if (customerId) {
        chargeData.customer_id = customerId;
      }
      
      console.log('=== SENDING CHARGE TO PAYARC ===');
      console.log('Charge data (sanitized):', {
        ...chargeData,
        card_number: `****${chargeData.card_number.slice(-4)}`,
        cvv: '***'
      });
      
      const chargeResponse = await axios.post(
        `${PAYARC_API_URL}/charges`,
        chargeData,
        {
          headers: {
            'Authorization': `Bearer ${PAYARC_API_TOKEN}`,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          timeout: 30000
        }
      );
      
      console.log('=== PAYARC RESPONSE RECEIVED ===');
      console.log('PayArc HTTP status:', chargeResponse.status);
      console.log('PayArc response headers:', JSON.stringify(chargeResponse.headers, null, 2));
      console.log('PayArc full response data:', JSON.stringify(chargeResponse.data, null, 2));
      
      const responseData = chargeResponse.data.data || chargeResponse.data;
      console.log('Extracted response data:', JSON.stringify(responseData, null, 2));
      console.log('Payment status from PayArc:', responseData.status);
      
      if (responseData.status === 'approved' || responseData.status === 'success' || responseData.status === 'captured') {
        paymentResult = {
          id: responseData.charge_id || responseData.id || responseData.transaction_id,
          status: 'succeeded',
          amount: amount * 100,
          test_mode: false
        };
        
        if (customerId) {
          await firestore.collection('users').doc(finalUserId).set({
            payarcCustomerId: customerId
          }, { merge: true });
        }
        
        console.log('PayArc payment successful! Charge ID:', paymentResult.id);
        
        try {
          if (customerId) {
            console.log('Setting up recurring subscription...');
            subscriptionId = `sub_${Date.now()}`;
          }
        } catch (subError) {
          console.error('Subscription setup error (non-fatal):', subError.message);
        }
      } else {
        console.error('=== PAYMENT NOT APPROVED ===');
        console.error('Payment status:', responseData.status);
        console.error('Decline reason:', responseData.reason || responseData.message || 'Unknown');
        console.error('Response code:', responseData.response_code || 'None');
        console.error('Gateway response:', responseData.gateway_response || 'None');
        throw new Error(responseData.reason || responseData.message || `Payment declined with status: ${responseData.status}`);
      }
    }
    
    // Calculate next billing date
    const nextBillingDate = new Date();
    nextBillingDate.setDate(nextBillingDate.getDate() + 30);
    
    // Save to Firestore
    const membershipData = {
      paymentId: paymentResult.id,
      subscriptionId: subscriptionId,
      amount: parseFloat(amount),
      status: 'active',
      membershipStatus: 'active',
      subscriptionStatus: 'active',
      subscriptionType: subscriptionType || 'individual',
      email: email,
      firstName: firstName || '',
      lastName: lastName || '',
      phone: phone || '',
      birthdate: birthdate || '',
      paymentProcessed: true,
      processedAt: admin.firestore.FieldValue.serverTimestamp(),
      lastPaymentDate: admin.firestore.FieldValue.serverTimestamp(),
      nextBillingDate: nextBillingDate.toISOString(),
      paymentMode: paymentMode,
      testMode: paymentResult.test_mode || false,
      billing_address: billing_address || '',
      city: city || '',
      state: state || '',
      zip: zip || '',
      country: country || 'US',
      cardLast4: cleanCardNumber.slice(-4),
      monthlyPremium: parseFloat(amount)
    };
    
    await firestore
      .collection('users')
      .doc(finalUserId)
      .set(membershipData, { merge: true });
    
    await firestore
      .collection('payments')
      .add({
        ...membershipData,
        userId: finalUserId
      });
    
    console.log('Payment saved to Firestore successfully');
    
    const successMessage = paymentResult.test_mode 
      ? 'TEST MODE: Payment simulation successful!' 
      : 'Payment processed successfully!';
    
    return {
      success: true,
      paymentId: paymentResult.id,
      subscriptionId: subscriptionId,
      userId: finalUserId,
      message: successMessage,
      error: null,
      testMode: paymentResult.test_mode || false,
      nextBillingDate: nextBillingDate.toISOString()
    };
    
  } catch (error) {
    console.error('=== PAYMENT PROCESSING ERROR ===');
    console.error('Error type:', error.constructor.name);
    console.error('Error message:', error.message);
    console.error('Error stack:', error.stack);
    
    if (error.response) {
      console.error('=== PAYARC ERROR RESPONSE DETAILS ===');
      console.error('HTTP Status:', error.response.status);
      console.error('Status Text:', error.response.statusText);
      console.error('Response Headers:', JSON.stringify(error.response.headers, null, 2));
      console.error('Full Error Response Data:', JSON.stringify(error.response.data, null, 2));
      
      const errorData = error.response.data;
      const errorMessage = errorData.message || errorData.error_message || errorData.reason || errorData.error;
      const errorCode = errorData.code || errorData.error_code || errorData.response_code;
      const declineReason = errorData.decline_reason || errorData.gateway_response;
      
      console.error('Extracted Error Code:', errorCode);
      console.error('Extracted Error Message:', errorMessage);
      console.error('Decline Reason:', declineReason);
      
      if (error.response.status === 401) {
        console.error('Authentication failed - API token may be invalid or expired');
        throw new functions.https.HttpsError(
          'unauthenticated',
          'PayArc authentication failed. Please contact support.'
        );
      } else if (error.response.status === 403) {
        console.error('Forbidden - Account may not be activated for live processing');
        throw new functions.https.HttpsError(
          'permission-denied',
          'Account not authorized for live processing. Please contact PayArc support to activate your merchant account.'
        );
      } else if (error.response.status === 402 || error.response.status === 422) {
        console.error('Payment declined by processor');
        const declineMessage = errorMessage || declineReason || 'Card was declined';
        throw new functions.https.HttpsError(
          'invalid-argument',
          `Payment declined: ${declineMessage}`
        );
      } else if (error.response.status === 400) {
        console.error('Bad request - Invalid payment data');
        throw new functions.https.HttpsError(
          'invalid-argument',
          `Invalid payment data: ${errorMessage || 'Please check card details'}`
        );
      } else if (error.response.status >= 500) {
        console.error('PayArc server error');
        throw new functions.https.HttpsError(
          'internal',
          'Payment processor is temporarily unavailable. Please try again in a few minutes.'
        );
      } else {
        console.error('Unhandled PayArc error status:', error.response.status);
        throw new functions.https.HttpsError(
          'internal',
          `Payment failed: ${errorMessage || 'Unknown error from payment processor'}`
        );
      }
    } else if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
      console.error('Request timeout error');
      throw new functions.https.HttpsError(
        'deadline-exceeded',
        'Payment request timed out. Please try again.'
      );
    } else if (error.code === 'ENOTFOUND' || error.code === 'ECONNREFUSED') {
      console.error('Network connectivity error');
      throw new functions.https.HttpsError(
        'unavailable',
        'Unable to connect to payment processor. Please try again.'
      );
    } else {
      console.error('Non-HTTP error occurred:', error);
      throw new functions.https.HttpsError(
        'internal',
        `Payment processing failed: ${error.message}`
      );
    }
  }
});

// Check PayArc Account Status
exports.checkPayArcAccountStatus = functions.https.onRequest(async (req, res) => {
  console.log('=== CHECKING PAYARC ACCOUNT STATUS ===');
  
  try {
    console.log('Testing PayArc API connection...');
    const accountResponse = await axios.get(
      `${PAYARC_API_URL}/account`,
      {
        headers: {
          'Authorization': `Bearer ${PAYARC_API_TOKEN}`,
          'Accept': 'application/json'
        },
        timeout: 10000
      }
    );
    
    console.log('Account response status:', accountResponse.status);
    console.log('PayArc account info:', JSON.stringify(accountResponse.data, null, 2));
    
    res.json({
      status: 'success',
      message: 'PayArc API connection successful',
      account: accountResponse.data,
      apiUrl: PAYARC_API_URL,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('=== PAYARC ACCOUNT CHECK FAILED ===');
    console.error('Error message:', error.message);
    
    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', JSON.stringify(error.response.data, null, 2));
    }
    
    res.json({
      status: 'error',
      message: 'PayArc API connection failed',
      error: error.response?.data || error.message,
      httpStatus: error.response?.status,
      apiUrl: PAYARC_API_URL,
      timestamp: new Date().toISOString()
    });
  }
});

// Test PayArc Connection
exports.testPayArcConnection = functions.https.onRequest(async (req, res) => {
  try {
    const testResponse = await axios.get(
      `${PAYARC_API_URL}/charges`,
      {
        headers: {
          'Authorization': `Bearer ${PAYARC_API_TOKEN}`,
          'Accept': 'application/json'
        },
        params: {
          limit: 1
        }
      }
    );
    
    res.json({
      status: 'ok',
      mode: 'live',
      connected: true,
      timestamp: new Date().toISOString(),
      message: 'PayArc API is connected and working'
    });
  } catch (error) {
    console.error('PayArc connection test failed:', error.message);
    res.json({
      status: 'ok',
      mode: 'test',
      connected: false,
      timestamp: new Date().toISOString(),
      message: 'PayArc connection failed - test mode available',
      error: error.message
    });
  }
});

// PayArc Webhook Handler
exports.payarcWebhook = functions.https.onRequest(async (req, res) => {
  console.log('PayArc webhook received:', {
    type: req.body.type,
    event: req.body.event,
    data: req.body.data ? 'Data received' : 'No data'
  });
  
  try {
    const event = req.body;
    
    if (event.type === 'charge.succeeded' || event.type === 'payment.success' || event.type === 'charge.captured') {
      console.log('Processing successful payment webhook');
      
      if (event.data) {
        let userId = null;
        
        if (event.data.customer_id) {
          const customerQuery = await firestore.collection('users')
            .where('payarcCustomerId', '==', event.data.customer_id)
            .limit(1)
            .get();
          
          if (!customerQuery.empty) {
            userId = customerQuery.docs[0].id;
          }
        }
        
        if (!userId && event.data.email) {
          const emailQuery = await firestore.collection('users')
            .where('email', '==', event.data.email)
            .limit(1)
            .get();
          
          if (!emailQuery.empty) {
            userId = emailQuery.docs[0].id;
          }
        }
        
        if (userId) {
          const nextBillingDate = new Date();
          nextBillingDate.setDate(nextBillingDate.getDate() + 30);
          
          await firestore.collection('users').doc(userId).update({
            subscriptionStatus: 'active',
            membershipStatus: 'active',
            lastPaymentDate: admin.firestore.FieldValue.serverTimestamp(),
            lastPaymentAmount: event.data.amount ? event.data.amount / 100 : null,
            nextBillingDate: nextBillingDate.toISOString(),
            consecutiveFailures: 0
          });
          
          await firestore.collection('payment_logs').add({
            userId: userId,
            type: 'recurring_payment',
            status: 'success',
            amount: event.data.amount ? event.data.amount / 100 : null,
            chargeId: event.data.id || event.data.charge_id,
            timestamp: admin.firestore.FieldValue.serverTimestamp()
          });
          
          console.log('User subscription updated for:', userId);
        }
      }
    } else if (event.type === 'charge.failed' || event.type === 'payment.failed') {
      console.log('Processing failed payment webhook');
      
      if (event.data) {
        let userId = null;
        
        if (event.data.customer_id) {
          const customerQuery = await firestore.collection('users')
            .where('payarcCustomerId', '==', event.data.customer_id)
            .limit(1)
            .get();
          
          if (!customerQuery.empty) {
            userId = customerQuery.docs[0].id;
          }
        }
        
        if (!userId && event.data.email) {
          const emailQuery = await firestore.collection('users')
            .where('email', '==', event.data.email)
            .limit(1)
            .get();
          
          if (!emailQuery.empty) {
            userId = emailQuery.docs[0].id;
          }
        }
        
        if (userId) {
          const userDoc = await firestore.collection('users').doc(userId).get();
          const userData = userDoc.data();
          const failures = (userData.consecutiveFailures || 0) + 1;
          
          await firestore.collection('users').doc(userId).update({
            subscriptionStatus: failures >= 3 ? 'suspended' : 'past_due',
            lastFailedPayment: admin.firestore.FieldValue.serverTimestamp(),
            consecutiveFailures: failures,
            failureReason: event.data.reason || event.data.message || 'Payment failed'
          });
          
          await firestore.collection('payment_logs').add({
            userId: userId,
            type: 'recurring_payment',
            status: 'failed',
            amount: event.data.amount ? event.data.amount / 100 : null,
            reason: event.data.reason || event.data.message,
            attemptNumber: failures,
            timestamp: admin.firestore.FieldValue.serverTimestamp()
          });
          
          console.log('Payment failed for user:', userId, 'Failure count:', failures);
        }
      }
    } else if (event.type === 'subscription.canceled' || event.type === 'subscription.deleted') {
      console.log('Processing subscription cancellation webhook');
      
      if (event.data && event.data.customer_id) {
        const customerQuery = await firestore.collection('users')
          .where('payarcCustomerId', '==', event.data.customer_id)
          .limit(1)
          .get();
        
        if (!customerQuery.empty) {
          const userId = customerQuery.docs[0].id;
          
          await firestore.collection('users').doc(userId).update({
            subscriptionStatus: 'canceled',
            membershipStatus: 'inactive',
            canceledAt: admin.firestore.FieldValue.serverTimestamp()
          });
          
          console.log('Subscription canceled for user:', userId);
        }
      }
    }
    
    res.status(200).json({ received: true });
  } catch (error) {
    console.error('Webhook processing error:', error);
    res.status(200).json({ received: true, error: error.message });
  }
});

// Cancel Membership
exports.cancelMembership = functions.https.onCall(async (data, context) => {
  if (!context.auth) {
    throw new functions.https.HttpsError('unauthenticated', 'User must be authenticated');
  }
  
  const userId = context.auth.uid;
  
  try {
    console.log('Canceling membership for user:', userId);
    
    const userDoc = await firestore.collection('users').doc(userId).get();
    
    if (!userDoc.exists) {
      throw new functions.https.HttpsError('not-found', 'User not found');
    }
    
    const userData = userDoc.data();
    
    let finalBillingDate = null;
    if (userData.nextBillingDate) {
      finalBillingDate = userData.nextBillingDate;
    } else {
      const date = new Date();
      date.setDate(date.getDate() + 30);
      finalBillingDate = date.toISOString();
    }
    
    await firestore.collection('users').doc(userId).update({
      subscriptionStatus: 'canceling',
      membershipStatus: 'active',
      canceledAt: admin.firestore.FieldValue.serverTimestamp(),
      cancelReason: data.reason || 'User requested cancellation',
      finalBillingDate: finalBillingDate,
      willCancelOn: finalBillingDate
    });
    
    if (userData.payarcCustomerId && userData.subscriptionId) {
      try {
        console.log('Attempting to cancel PayArc subscription:', userData.subscriptionId);
      } catch (payarcError) {
        console.error('PayArc cancellation error (non-fatal):', payarcError.message);
      }
    }
    
    await firestore.collection('cancellations').add({
      userId: userId,
      reason: data.reason || 'User requested',
      canceledAt: admin.firestore.FieldValue.serverTimestamp(),
      finalBillingDate: finalBillingDate,
      immediatelyCanceled: data.immediately || false
    });
    
    console.log('Membership canceled successfully for:', userId);
    
    if (data.immediately === true) {
      await firestore.collection('users').doc(userId).update({
        subscriptionStatus: 'canceled',
        membershipStatus: 'inactive'
      });
      
      return {
        success: true,
        message: 'Your membership has been canceled immediately. You no longer have access to services.'
      };
    }
    
    return {
      success: true,
      message: `Your membership has been scheduled for cancellation. You will retain access until ${new Date(finalBillingDate).toLocaleDateString()}.`,
      finalBillingDate: finalBillingDate
    };
    
  } catch (error) {
    console.error('Error canceling membership:', error);
    
    if (error instanceof functions.https.HttpsError) {
      throw error;
    }
    
    throw new functions.https.HttpsError('internal', 'Failed to cancel membership. Please try again or contact support.');
  }
});

// Update Membership Payment
exports.updateMembershipPayment = functions.https.onCall(async (data, context) => {
  if (!context.auth) {
    throw new functions.https.HttpsError('unauthenticated', 'User must be authenticated');
  }
  
  const userId = context.auth.uid;
  console.log('Updating membership payment for user:', userId);
  
  return exports.processMembershipPayment({
    ...data,
    userId: userId,
    isUpdate: true
  }, context);
});


// ============================================
// EMAIL FUNCTIONS (SendGrid)
// ============================================

// Send Welcome Email
exports.sendWelcomeEmail = functions.https.onCall(async (data, context) => {
  console.log('=== Welcome Email Request Received ===');
  
  const sendgridKey = process.env.SENDGRID_API_KEY || process.env.sendgrid_key;
  if (!sendgridKey) {
    console.error('SendGrid API key not configured');
    throw new functions.https.HttpsError(
      'failed-precondition',
      'Email service not configured. Please contact support.'
    );
  }
  sgMail.setApiKey(sendgridKey);
  
  if (!context.auth) {
    throw new functions.https.HttpsError(
      'unauthenticated',
      'User must be authenticated'
    );
  }

  const {
    firstName,
    lastName,
    email,
    planType,
    totalPremium,
    deductible,
    memberCount,
    dentalCoverage,
    visionCoverage,
  } = data;

  if (!firstName || !email) {
    throw new functions.https.HttpsError(
      'invalid-argument',
      'Missing required fields: firstName and email are required'
    );
  }

  console.log('Sending welcome email to:', email);
  console.log('Plan type:', planType);
  console.log('Premium:', totalPremium);

  const currentYear = new Date().getFullYear();

  const msg = {
    to: email,
    from: {
      email: 'welcome@kurv.health',
      name: 'Kurv Health',
    },
    replyTo: 'support@kurv.health',
    subject: `🎉 Welcome to Kurv Health, ${firstName}!`,
    templateId: 'd-11ad1855b5b742c9a87aa59f17e4c35b',
    dynamicTemplateData: {
      first_name: firstName,
      last_name: lastName || '',
      email: email,
      plan_type: planType || 'Individual',
      total_premium: parseFloat(totalPremium || 0).toFixed(2),
      deductible: deductible || '1500',
      member_count: memberCount || '1',
      dental_coverage: dentalCoverage || false,
      vision_coverage: visionCoverage || false,
      dashboard_url: 'https://app.kurvhealth.com/home',
      privacy_url: 'https://kurvhealth.com/privacy',
      terms_url: 'https://kurvhealth.com/terms',
      unsubscribe_url: `https://kurvhealth.com/unsubscribe?email=${encodeURIComponent(email)}`,
      current_year: currentYear.toString(),
    },
  };

  try {
    await sgMail.send(msg);
    console.log(`Welcome email sent successfully to ${email}`);
    
    const userId = context.auth.uid;
    await firestore.collection('users').doc(userId).update({
      welcomeEmailSent: true,
      welcomeEmailSentAt: admin.firestore.FieldValue.serverTimestamp(),
    });
    
    return { success: true, message: 'Welcome email sent successfully' };
  } catch (error) {
    console.error('SendGrid error:', error);
    if (error.response) {
      console.error('SendGrid error body:', error.response.body);
    }
    throw new functions.https.HttpsError(
      'internal',
      'Failed to send welcome email: ' + error.message
    );
  }
});

// Send Appointment Confirmation Email
exports.sendAppointmentConfirmation = functions.https.onCall(async (data, context) => {
  console.log('=== Appointment Confirmation Email Request Received ===');
  
  const sendgridKey = process.env.SENDGRID_API_KEY || process.env.sendgrid_key;
  if (!sendgridKey) {
    console.error('SendGrid API key not configured');
    throw new functions.https.HttpsError(
      'failed-precondition',
      'Email service not configured. Please contact support.'
    );
  }
  sgMail.setApiKey(sendgridKey);

  const {
    email,
    patientName,
    visitType,
    visitMode,
    symptom,
    appointmentDate,
    appointmentTime,
    requestId,
    clinic,
    selectedBeverage,
    selectedTeaType,
    hasPriority,
  } = data;

  if (!email || !patientName || !visitType) {
    throw new functions.https.HttpsError(
      'invalid-argument',
      'Missing required fields: email, patientName, and visitType are required'
    );
  }

  console.log('Sending appointment confirmation email to:', email);
  console.log('Visit type:', visitType);
  console.log('Appointment date:', appointmentDate);

  let formattedDate = 'Not specified';
  if (appointmentDate) {
    try {
      const date = new Date(appointmentDate);
      formattedDate = date.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch (error) {
      console.error('Error formatting date:', error);
    }
  }

  let beverageText = '';
  if (selectedBeverage) {
    beverageText = selectedBeverage;
    if (selectedTeaType) {
      beverageText += ` (${selectedTeaType})`;
    }
  }

  const emailHtml = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      line-height: 1.6;
      color: #333;
      max-width: 600px;
      margin: 0 auto;
      padding: 20px;
      background-color: #f5f7fa;
    }
    .container {
      background-color: #ffffff;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      overflow: hidden;
    }
    .header {
      background: linear-gradient(135deg, #1066ED 0%, #0B3896 100%);
      color: white;
      padding: 30px 20px;
      text-align: center;
    }
    .header h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 600;
    }
    .header p {
      margin: 10px 0 0 0;
      font-size: 16px;
      opacity: 0.9;
    }
    .content {
      padding: 30px 20px;
    }
    .appointment-card {
      background: linear-gradient(135deg, #f0f7ff 0%, #e6f2ff 100%);
      border-left: 4px solid #1066ED;
      padding: 20px;
      margin: 20px 0;
      border-radius: 8px;
    }
    .appointment-card h2 {
      margin: 0 0 15px 0;
      color: #1066ED;
      font-size: 20px;
    }
    .detail-row {
      display: flex;
      padding: 8px 0;
      border-bottom: 1px solid rgba(16, 102, 237, 0.1);
    }
    .detail-row:last-child {
      border-bottom: none;
    }
    .detail-label {
      font-weight: 600;
      color: #555;
      min-width: 140px;
    }
    .detail-value {
      color: #333;
      flex: 1;
    }
    .priority-badge {
      display: inline-block;
      background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
      color: white;
      padding: 8px 16px;
      border-radius: 20px;
      font-weight: 600;
      font-size: 14px;
      margin: 10px 0;
    }
    .beverage-section {
      background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
      border-left: 4px solid #10b981;
      padding: 15px;
      margin: 20px 0;
      border-radius: 8px;
    }
    .beverage-section h3 {
      margin: 0 0 8px 0;
      color: #059669;
      font-size: 16px;
    }
    .info-box {
      background-color: #fff8e6;
      border-left: 4px solid #fbbf24;
      padding: 15px;
      margin: 20px 0;
      border-radius: 8px;
    }
    .button {
      display: inline-block;
      background: linear-gradient(135deg, #1066ED 0%, #0B3896 100%);
      color: white !important;
      padding: 14px 28px;
      text-decoration: none;
      border-radius: 8px;
      font-weight: 600;
      margin: 20px 0;
      text-align: center;
    }
    .footer {
      background-color: #f5f7fa;
      padding: 20px;
      text-align: center;
      font-size: 14px;
      color: #666;
    }
    .footer a {
      color: #1066ED;
      text-decoration: none;
    }
    @media only screen and (max-width: 600px) {
      body {
        padding: 10px;
      }
      .content {
        padding: 20px 15px;
      }
      .detail-row {
        flex-direction: column;
      }
      .detail-label {
        margin-bottom: 4px;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>✓ Appointment Confirmed</h1>
      <p>Your appointment has been successfully scheduled</p>
    </div>
    
    <div class="content">
      <p>Hello <strong>${patientName}</strong>,</p>
      
      <p>Thank you for scheduling your appointment with Kurv Health. We've confirmed your visit details below:</p>
      
      ${hasPriority ? '<div class="priority-badge">⚡ PRIORITY SERVICE - Skip the wait!</div>' : ''}
      
      <div class="appointment-card">
        <h2>📅 Appointment Details</h2>
        <div class="detail-row">
          <span class="detail-label">Patient:</span>
          <span class="detail-value">${patientName}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Visit Type:</span>
          <span class="detail-value">${visitType}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Visit Mode:</span>
          <span class="detail-value">${visitMode}</span>
        </div>
        ${symptom ? `
        <div class="detail-row">
          <span class="detail-label">Reason:</span>
          <span class="detail-value">${symptom}</span>
        </div>
        ` : ''}
        ${formattedDate !== 'Not specified' ? `
        <div class="detail-row">
          <span class="detail-label">Date:</span>
          <span class="detail-value">${formattedDate}</span>
        </div>
        ` : ''}
        ${appointmentTime ? `
        <div class="detail-row">
          <span class="detail-label">Time:</span>
          <span class="detail-value">${appointmentTime}</span>
        </div>
        ` : ''}
        ${clinic ? `
        <div class="detail-row">
          <span class="detail-label">Clinic:</span>
          <span class="detail-value">${clinic}</span>
        </div>
        ` : ''}
        ${requestId ? `
        <div class="detail-row">
          <span class="detail-label">Confirmation #:</span>
          <span class="detail-value">${requestId}</span>
        </div>
        ` : ''}
      </div>
      
      ${beverageText ? `
      <div class="beverage-section">
        <h3>☕ Complimentary Beverage</h3>
        <p style="margin: 0;">Your <strong>${beverageText}</strong> will be ready when you arrive at the clinic.</p>
      </div>
      ` : ''}
      
      ${visitMode === 'Clinic' ? `
      <div class="info-box">
        <strong>📍 Important Reminders:</strong>
        <ul style="margin: 10px 0 0 0; padding-left: 20px;">
          <li>Please arrive 15 minutes early for check-in</li>
          <li>Bring a valid ID and insurance card</li>
          <li>Wear a mask if you have respiratory symptoms</li>
          ${hasPriority ? '<li>Show this email to skip the regular waiting line</li>' : ''}
        </ul>
      </div>
      ` : ''}
      
      ${visitMode === 'Virtual' ? `
      <div class="info-box">
        <strong>💻 Virtual Visit Information:</strong>
        <ul style="margin: 10px 0 0 0; padding-left: 20px;">
          <li>You will receive a video call link 30 minutes before your appointment</li>
          <li>Make sure you have a stable internet connection</li>
          <li>Test your camera and microphone beforehand</li>
          <li>Find a quiet, private space for your consultation</li>
        </ul>
      </div>
      ` : ''}
      
      <center>
        <a href="https://app.kurvhealth.com/myAppointment" class="button">View My Appointments</a>
      </center>
      
      <p style="margin-top: 30px;">Need to reschedule or have questions? Contact us at <a href="tel:+18004589" style="color: #1066ED; text-decoration: none;">1-800-458-9</a> or reply to this email.</p>
      
      <p>We look forward to seeing you!</p>
      
      <p style="margin-top: 20px;">
        <strong>The Kurv Health Team</strong><br>
        <a href="mailto:support@kurv.health" style="color: #1066ED; text-decoration: none;">support@kurv.health</a>
      </p>
    </div>
    
    <div class="footer">
      <p>
        <a href="https://kurvhealth.com">Kurv Health</a> | 
        <a href="https://kurvhealth.com/privacy">Privacy Policy</a> | 
        <a href="https://kurvhealth.com/terms">Terms of Service</a>
      </p>
      <p style="margin-top: 10px; font-size: 12px; color: #999;">
        © ${new Date().getFullYear()} Kurv Health. All rights reserved.
      </p>
    </div>
  </div>
</body>
</html>
  `;

  const msg = {
    to: email,
    from: {
      email: 'appointments@kurv.health',
      name: 'Kurv Health Appointments',
    },
    replyTo: 'support@kurv.health',
    subject: `Appointment Confirmed - ${patientName} - ${formattedDate}`,
    html: emailHtml,
  };

  try {
    await sgMail.send(msg);
    console.log(`Appointment confirmation email sent successfully to ${email}`);
    
    return { 
      success: true, 
      message: 'Appointment confirmation email sent successfully' 
    };
  } catch (error) {
    console.error('SendGrid error sending appointment confirmation:', error);
    if (error.response) {
      console.error('SendGrid error body:', error.response.body);
    }
    console.log('Email failed but returning success to avoid blocking appointment');
    return { 
      success: false, 
      message: 'Appointment created but email failed: ' + error.message 
    };
  }
});

// Send Receipt Confirmation Email
exports.sendReceiptConfirmation = functions.https.onCall(async (data, context) => {
  console.log('=== Receipt Confirmation Email Request Received ===');
  
  const sendgridKey = process.env.SENDGRID_API_KEY || process.env.sendgrid_key;
  if (!sendgridKey) {
    console.error('SendGrid API key not configured');
    throw new functions.https.HttpsError(
      'failed-precondition',
      'Email service not configured. Please contact support.'
    );
  }
  sgMail.setApiKey(sendgridKey);

  const {
    email,
    patientName,
    amount,
    date,
    confirmationId,
    submittedAt,
    deductibleTotal,
    paidAmount,
    deductibleRemaining,
    deductibleProgress,
    deductibleMet,
  } = data;

  if (!email || !patientName || !amount) {
    throw new functions.https.HttpsError(
      'invalid-argument',
      'Missing required fields: email, patientName, and amount are required'
    );
  }

  console.log('Sending receipt confirmation email to:', email);
  console.log('Amount:', amount);
  console.log('Deductible met:', deductibleMet);

  const msg = {
    to: email,
    from: {
      email: 'receipts@kurv.health',
      name: 'Kurv Health',
    },
    replyTo: 'support@kurv.health',
    subject: `Receipt Uploaded - $${amount} - Kurv Health`,
    templateId: 'd-f216f62316094d309c5389b1c95d8824',
    dynamicTemplateData: {
      patientName: patientName,
      amount: amount,
      date: date,
      confirmationId: confirmationId || 'N/A',
      submittedAt: submittedAt || new Date().toLocaleString(),
      deductibleTotal: deductibleTotal || '0',
      paidAmount: paidAmount || '0',
      deductibleRemaining: deductibleRemaining || '0',
      deductibleProgress: deductibleProgress || 0,
      deductibleMet: deductibleMet || false,
      unsubscribe_url: `https://kurvhealth.com/unsubscribe?email=${encodeURIComponent(email)}`,
    },
  };

  try {
    await sgMail.send(msg);
    console.log(`Receipt confirmation email sent successfully to ${email}`);
    
    return { 
      success: true, 
      message: 'Receipt confirmation email sent successfully' 
    };
  } catch (error) {
    console.error('SendGrid error sending receipt confirmation:', error);
    if (error.response) {
      console.error('SendGrid error body:', error.response.body);
    }
    console.log('Email failed but returning success to avoid blocking receipt upload');
    return { 
      success: false, 
      message: 'Receipt uploaded but email failed: ' + error.message 
    };
  }
});

// Send Claim Confirmation Email
exports.sendClaimConfirmation = functions.https.onCall(async (data, context) => {
  console.log('=== Claim Confirmation Email Request Received ===');
  
  const sendgridKey = process.env.SENDGRID_API_KEY || process.env.sendgrid_key;
  if (!sendgridKey) {
    console.error('SendGrid API key not configured');
    throw new functions.https.HttpsError(
      'failed-precondition',
      'Email service not configured. Please contact support.'
    );
  }
  sgMail.setApiKey(sendgridKey);

  const {
    email,
    patientName,
    provider,
    reason,
    amount,
    date,
    claimId,
    submittedAt,
    status,
    paymentProcessed,
    paymentId,
  } = data;

  if (!email || !patientName || !amount || !provider) {
    throw new functions.https.HttpsError(
      'invalid-argument',
      'Missing required fields: email, patientName, amount, and provider are required'
    );
  }

  console.log('Sending claim confirmation email to:', email);
  console.log('Claim amount:', amount);
  console.log('Payment processed:', paymentProcessed);
  console.log('Status:', status);

  const msg = {
    to: email,
    from: {
      email: 'claims@kurv.health',
      name: 'Kurv Health Claims',
    },
    replyTo: 'support@kurv.health',
    subject: `Claim Submitted - $${amount} - Kurv Health`,
    templateId: 'd-4095be4538eb421fb2ac0c3fd8c7abc8',
    dynamicTemplateData: {
      patientName: patientName,
      provider: provider,
      reason: reason || 'Medical services',
      amount: amount,
      date: date,
      claimId: claimId || 'N/A',
      submittedAt: submittedAt || new Date().toLocaleString(),
      status: status || 'Pending',
      paymentProcessed: paymentProcessed || false,
      paymentId: paymentId || null,
      unsubscribe_url: `https://kurvhealth.com/unsubscribe?email=${encodeURIComponent(email)}`,
    },
  };

  try {
    await sgMail.send(msg);
    console.log(`Claim confirmation email sent successfully to ${email}`);
    
    return { 
      success: true, 
      message: 'Claim confirmation email sent successfully' 
    };
  } catch (error) {
    console.error('SendGrid error sending claim confirmation:', error);
    if (error.response) {
      console.error('SendGrid error body:', error.response.body);
    }
    console.log('Email failed but returning success to avoid blocking claim submission');
    return { 
      success: false, 
      message: 'Claim submitted but email failed: ' + error.message 
    };
  }
});


// ============================================
// PUSH NOTIFICATION FUNCTIONS
// ============================================

// Add FCM Token
exports.addFcmToken = functions.https.onCall(async (data, context) => {
  if (!context.auth) {
    return 'Failed: Unauthenticated calls are not allowed.';
  }
  const userDocPath = data.userDocPath;
  const fcmToken = data.fcmToken;
  const deviceType = data.deviceType;
  if (
    typeof userDocPath === 'undefined' ||
    typeof fcmToken === 'undefined' ||
    typeof deviceType === 'undefined' ||
    userDocPath.split('/').length <= 1 ||
    fcmToken.length === 0 ||
    deviceType.length === 0
  ) {
    return 'Invalid arguments encountered when adding FCM token.';
  }
  if (context.auth.uid != userDocPath.split('/')[1]) {
    return "Failed: Authenticated user doesn't match user provided.";
  }
  const existingTokens = await firestore
    .collectionGroup(kFcmTokensCollection)
    .where('fcm_token', '==', fcmToken)
    .get();
  var userAlreadyHasToken = false;
  for (var doc of existingTokens.docs) {
    const user = doc.ref.parent.parent;
    if (user.path != userDocPath) {
      await doc.ref.delete();
    } else {
      userAlreadyHasToken = true;
    }
  }
  if (userAlreadyHasToken) {
    return 'FCM token already exists for this user. Ignoring...';
  }
  await getUserFcmTokensCollection(userDocPath).doc().set({
    fcm_token: fcmToken,
    device_type: deviceType,
    created_at: admin.firestore.FieldValue.serverTimestamp(),
  });
  return 'Successfully added FCM token!';
});

// Send Push Notifications Trigger - REMOVED runWith for compatibility
exports.sendPushNotificationsTrigger = functions.firestore
  .document(`${kPushNotificationsCollection}/{id}`)
  .onCreate(async (snapshot, _) => {
    try {
      const scheduledTime = snapshot.data().scheduled_time || '';
      if (scheduledTime) {
        return;
      }
      await sendPushNotifications(snapshot);
    } catch (e) {
      console.log(`Error: ${e}`);
      await snapshot.ref.update({ status: 'failed', error: `${e}` });
    }
  });

// Send Scheduled Push Notifications
exports.sendScheduledPushNotifications = functions.pubsub
  .schedule(`every ${kSchedulerIntervalMinutes} minutes synchronized`)
  .onRun(async (_) => {
    const minutesToMilliseconds = (minutes) => minutes * 60 * 1000;
    function currentTimeDownToNearestMinute() {
      const currentTime = new Date(new Date().getTime() + 1000);
      currentTime.setSeconds(0, 0);
      return currentTime;
    }

    const intervalMs = minutesToMilliseconds(kSchedulerIntervalMinutes);
    const upperCutoffTime = currentTimeDownToNearestMinute();
    const lowerCutoffTime = new Date(upperCutoffTime.getTime() - intervalMs);
    
    const scheduledNotifications = await firestore
      .collection(kPushNotificationsCollection)
      .where('scheduled_time', '>', lowerCutoffTime)
      .where('scheduled_time', '<=', upperCutoffTime)
      .get();
    for (var snapshot of scheduledNotifications.docs) {
      try {
        await sendPushNotifications(snapshot);
      } catch (e) {
        console.log(`Error: ${e}`);
        await snapshot.ref.update({ status: 'failed', error: `${e}` });
      }
    }
  });

// Helper function to send push notifications
async function sendPushNotifications(snapshot) {
  const notificationData = snapshot.data();
  const title = notificationData.notification_title || '';
  const body = notificationData.notification_text || '';
  const imageUrl = notificationData.notification_image_url || '';
  const sound = notificationData.notification_sound || '';
  const parameterData = notificationData.parameter_data || '';
  const targetAudience = notificationData.target_audience || '';
  const initialPageName = notificationData.initial_page_name || '';
  const userRefsStr = notificationData.user_refs || '';
  const batchIndex = notificationData.batch_index || 0;
  const numBatches = notificationData.num_batches || 0;
  const status = notificationData.status || '';

  if (status !== '' && status !== 'started') {
    console.log(`Already processed ${snapshot.ref.path}. Skipping...`);
    return;
  }

  if (title === '' || body === '') {
    await snapshot.ref.update({ status: 'failed' });
    return;
  }

  const userRefs = userRefsStr === '' ? [] : userRefsStr.trim().split(',');
  var tokens = new Set();
  if (userRefsStr) {
    for (var userRef of userRefs) {
      const userTokens = await firestore
        .doc(userRef)
        .collection(kFcmTokensCollection)
        .get();
      userTokens.docs.forEach((token) => {
        if (typeof token.data().fcm_token !== undefined) {
          tokens.add(token.data().fcm_token);
        }
      });
    }
  } else {
    var userTokensQuery = firestore.collectionGroup(kFcmTokensCollection);
    if (numBatches > 0) {
      userTokensQuery = userTokensQuery
        .orderBy(admin.firestore.FieldPath.documentId())
        .startAt(getDocIdBound(batchIndex, numBatches))
        .endBefore(getDocIdBound(batchIndex + 1, numBatches));
    }
    const userTokens = await userTokensQuery.get();
    userTokens.docs.forEach((token) => {
      const data = token.data();
      const audienceMatches =
        targetAudience === 'All' || data.device_type === targetAudience;
      if (audienceMatches && typeof data.fcm_token !== undefined) {
        tokens.add(data.fcm_token);
      }
    });
  }

  const tokensArr = Array.from(tokens);
  var messageBatches = [];
  for (let i = 0; i < tokensArr.length; i += 500) {
    const tokensBatch = tokensArr.slice(i, Math.min(i + 500, tokensArr.length));
    const messages = {
      notification: {
        title,
        body,
        ...(imageUrl && { imageUrl: imageUrl }),
      },
      data: {
        initialPageName,
        parameterData
      },
      android: {
        notification: {
          ...(sound && { sound: sound }),
        },
      },
      apns: {
        payload: {
          aps: {
            ...(sound && { sound: sound }),
          },
        },
      },
      tokens: tokensBatch,
    };
    messageBatches.push(messages);
  }

  var numSent = 0;
  await Promise.all(
    messageBatches.map(async (messages) => {
      const response = await admin.messaging().sendEachForMulticast(messages);
      numSent += response.successCount;
    })
  );

  await snapshot.ref.update({ status: 'succeeded', num_sent: numSent });
}

// Helper function to get user FCM tokens collection
function getUserFcmTokensCollection(userDocPath) {
  return firestore.doc(userDocPath).collection(kFcmTokensCollection);
}

// Helper function to get document ID bound for batching
function getDocIdBound(index, numBatches) {
  if (index <= 0) {
    return 'admin_users/(';
  }
  if (index >= numBatches) {
    return 'admin_users/}';
  }
  const numUidChars = 62;
  const twoCharOptions = Math.pow(numUidChars, 2);

  var twoCharIdx = (index * twoCharOptions) / numBatches;
  var firstCharIdx = Math.floor(twoCharIdx / numUidChars);
  var secondCharIdx = Math.floor(twoCharIdx % numUidChars);
  const firstChar = getCharForIndex(firstCharIdx);
  const secondChar = getCharForIndex(secondCharIdx);
  return 'admin_users/' + firstChar + secondChar;
}

// Helper function to get character for index
function getCharForIndex(charIdx) {
  if (charIdx < 10) {
    return String.fromCharCode(charIdx + '0'.charCodeAt(0));
  } else if (charIdx < 36) {
    return String.fromCharCode('A'.charCodeAt(0) + charIdx - 10);
  } else {
    return String.fromCharCode('a'.charCodeAt(0) + charIdx - 36);
  }
}

// Account deletion: full data wipe on auth user delete (see deleteUserData.js)
exports.deleteUserData = require("./deleteUserData").deleteUserData;

// Notification inbox + push + medication reminder scheduler (see notifications.js)
Object.assign(exports, require("./notifications"));

// ── Staff app (jovi-admin) functions ─────────────────────────────────────
exports.scribe = require('./scribe').scribe;
Object.assign(exports, require('./orders'));   // transmitOrder, labResultsWebhook
Object.assign(exports, require('./fax'));      // sendFax, faxInboundWebhook
exports.fhir = require('./fhir').fhir;
