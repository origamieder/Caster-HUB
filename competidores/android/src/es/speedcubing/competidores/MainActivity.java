package es.speedcubing.competidores;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends Activity {
    private WebView web;
    private final Handler ui = new Handler(Looper.getMainLooper());

    /** Puente para la web: descargas de la WCA (sin restricciones CORS) y compartir texto. */
    public class Native {
        @JavascriptInterface
        public void get(final String url, final String cbId) {
            new Thread(new Runnable() {
                public void run() {
                    boolean ok = false;
                    String body;
                    try {
                        if (!url.startsWith("https://www.worldcubeassociation.org/")) throw new Exception("URL no permitida");
                        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
                        c.setConnectTimeout(15000);
                        c.setReadTimeout(60000);
                        c.setRequestProperty("User-Agent", "cto-espana-2026-competidores");
                        c.setRequestProperty("Accept", "application/json");
                        int code = c.getResponseCode();
                        if (code != 200) throw new Exception("HTTP " + code);
                        InputStream in = c.getInputStream();
                        ByteArrayOutputStream out = new ByteArrayOutputStream();
                        byte[] buf = new byte[16384];
                        int n;
                        while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
                        in.close();
                        body = out.toString("UTF-8");
                        ok = true;
                    } catch (Exception e) {
                        body = String.valueOf(e.getMessage());
                    }
                    final String js = "window.__nativeDone(" + JSONObject.quote(cbId) + "," + ok + "," + JSONObject.quote(body) + ")";
                    ui.post(new Runnable() { public void run() { web.evaluateJavascript(js, null); } });
                }
            }).start();
        }

        @JavascriptInterface
        public void share(final String text) {
            ui.post(new Runnable() {
                public void run() {
                    Intent i = new Intent(Intent.ACTION_SEND);
                    i.setType("text/plain");
                    i.putExtra(Intent.EXTRA_TEXT, text);
                    try { startActivity(Intent.createChooser(i, "Compartir mis tiempos")); } catch (Exception ignored) { }
                }
            });
        }
    }

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.parseColor("#0D1330"));
        getWindow().setNavigationBarColor(Color.parseColor("#0D1330"));

        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#0D1330"));
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setBuiltInZoomControls(false);
        s.setSupportMultipleWindows(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        web.addJavascriptInterface(new Native(), "Native");

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                Uri u = Uri.parse(url);
                String scheme = u.getScheme();
                if ("http".equals(scheme) || "https".equals(scheme)) {
                    // WCA Live, perfiles WCA y reglamento: en el navegador; la app se queda donde estaba.
                    try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch (Exception ignored) { }
                    return true;
                }
                return false;
            }
        });

        setContentView(web);
        if (state != null) web.restoreState(state);
        else web.loadUrl("file:///android_asset/index.html");
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    public void onBackPressed() {
        // La web decide: cierra el teclado de tiempos o vuelve atrás; en Inicio, sale de la app.
        web.evaluateJavascript("(window.__back && window.__back()) ? 1 : 0", new ValueCallback<String>() {
            public void onReceiveValue(String v) {
                if (!"1".equals(v)) finish();
            }
        });
    }
}
