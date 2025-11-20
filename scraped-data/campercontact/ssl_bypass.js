/**
 * Universal SSL Pinning Bypass Script for Frida
 *
 * Usage:
 *   frida -U -f com.campercontact.app -l ssl_bypass.js --no-pause
 *
 * This script bypasses common SSL pinning implementations on Android
 */

console.log("[*] SSL Pinning Bypass Script Loaded");

// Hook Java's SSLContext
Java.perform(function() {
    console.log("[*] Hooking SSLContext");

    try {
        var SSLContext = Java.use('javax.net.ssl.SSLContext');
        var TrustManager = Java.use('javax.net.ssl.TrustManager');
        var X509TrustManager = Java.use('javax.net.ssl.X509TrustManager');

        var TrustManagerImpl = Java.registerClass({
            name: 'com.frida.TrustManagerImpl',
            implements: [X509TrustManager],
            methods: {
                checkClientTrusted: function(chain, authType) {
                    console.log("[*] checkClientTrusted called");
                },
                checkServerTrusted: function(chain, authType) {
                    console.log("[*] checkServerTrusted called - bypassing");
                },
                getAcceptedIssuers: function() {
                    console.log("[*] getAcceptedIssuers called");
                    return [];
                }
            }
        });

        SSLContext.init.overload('[Ljavax.net.ssl.KeyManager;', '[Ljavax.net.ssl.TrustManager;', 'java.security.SecureRandom').implementation = function(keyManager, trustManager, secureRandom) {
            console.log("[*] SSLContext.init() called - injecting custom TrustManager");
            var customTrustManager = TrustManagerImpl.$new();
            this.init(keyManager, [customTrustManager], secureRandom);
        };
        console.log("[+] SSLContext hooked successfully");
    } catch(e) {
        console.log("[-] SSLContext hook failed: " + e);
    }

    // Hook OkHttp Certificate Pinner
    try {
        console.log("[*] Hooking OkHttp CertificatePinner");
        var CertificatePinner = Java.use('okhttp3.CertificatePinner');

        CertificatePinner.check.overload('java.lang.String', 'java.util.List').implementation = function(hostname, peerCertificates) {
            console.log("[*] CertificatePinner.check() called for: " + hostname + " - bypassing");
            return;
        };
        console.log("[+] OkHttp CertificatePinner hooked successfully");
    } catch(e) {
        console.log("[-] OkHttp hook failed (might not be used): " + e);
    }

    // Hook Conscrypt TrustManager
    try {
        console.log("[*] Hooking Conscrypt TrustManager");
        var ConscryptTrustManager = Java.use('com.android.org.conscrypt.TrustManagerImpl');

        ConscryptTrustManager.checkTrustedRecursive.implementation = function() {
            console.log("[*] ConscryptTrustManager.checkTrustedRecursive() called - bypassing");
            return Java.use("java.util.ArrayList").$new();
        };
        console.log("[+] Conscrypt TrustManager hooked successfully");
    } catch(e) {
        console.log("[-] Conscrypt hook failed: " + e);
    }

    // Hook Apache HTTP Client
    try {
        console.log("[*] Hooking Apache HTTP Client");
        var SSLSocketFactory = Java.use('org.apache.http.conn.ssl.SSLSocketFactory');

        SSLSocketFactory.isSecure.overload('java.net.Socket').implementation = function(socket) {
            console.log("[*] SSLSocketFactory.isSecure() called - returning true");
            return true;
        };
        console.log("[+] Apache HTTP Client hooked successfully");
    } catch(e) {
        console.log("[-] Apache HTTP Client hook failed: " + e);
    }

    console.log("[*] All hooks attempted. If the app still fails, it may use native pinning.");
    console.log("[*] Check for libraries like: libflutter.so, libcurl.so, or custom native code");
});

// Hook native SSL functions (for apps using native code)
if (Process.platform === 'android') {
    console.log("[*] Attempting native SSL hooks");

    try {
        // Hook SSL_CTX_set_custom_verify
        var SSL_CTX_set_custom_verify = Module.findExportByName("libssl.so", "SSL_CTX_set_custom_verify");
        if (SSL_CTX_set_custom_verify) {
            Interceptor.attach(SSL_CTX_set_custom_verify, {
                onEnter: function(args) {
                    console.log("[*] SSL_CTX_set_custom_verify called - bypassing");
                }
            });
            console.log("[+] Native SSL_CTX_set_custom_verify hooked");
        }

        // Hook SSL_get_verify_result
        var SSL_get_verify_result = Module.findExportByName("libssl.so", "SSL_get_verify_result");
        if (SSL_get_verify_result) {
            Interceptor.replace(SSL_get_verify_result, new NativeCallback(function(ssl) {
                console.log("[*] SSL_get_verify_result called - returning 0 (OK)");
                return 0; // X509_V_OK
            }, 'int', ['pointer']));
            console.log("[+] Native SSL_get_verify_result hooked");
        }
    } catch(e) {
        console.log("[-] Native SSL hooks failed: " + e);
    }
}

console.log("[*] SSL Pinning Bypass Script Ready!");
console.log("[*] Now use the app and check mitmproxy for captured traffic");
