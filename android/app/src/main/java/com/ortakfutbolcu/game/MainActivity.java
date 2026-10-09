package com.ortakfutbolcu.game;

import android.app.Activity;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.Manifest;
import android.content.pm.PackageManager;
import android.webkit.JavascriptInterface;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.ConnectivityManager;
import android.net.NetworkCapabilities;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.JsPromptResult;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Button;
import android.widget.Toast;

public final class MainActivity extends Activity {
    private static final String HOME = "https://ortak-futbolcu.onrender.com/";
    private static final String HOST = "ortak-futbolcu.onrender.com";
    private WebView webView;
    private FrameLayout root;
    private View offlineView;
    private boolean loadingError;
    private static final String SOCIAL_CHANNEL = "ortakfutbolcu.social";
    private int notificationCounter = 200;

    public final class NativeBridge {
        @JavascriptInterface public void notify(String title, String body) {
            // WebView only loads the trusted Ortak Futbolcu origin.
            runOnUiThread(() -> postGameNotification(title, body));
        }
    }

    private void postGameNotification(String title, String body) {
        NotificationManager manager=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
        if (manager==null) return;
        if (Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED) return;
        Intent open=new Intent(this,MainActivity.class);
        open.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent intent=PendingIntent.getActivity(this,0,open,PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder builder=Build.VERSION.SDK_INT>=26
            ? new Notification.Builder(this,SOCIAL_CHANNEL) : new Notification.Builder(this);
        builder.setSmallIcon(android.R.drawable.ic_dialog_info)
           .setContentTitle(title).setContentText(body).setAutoCancel(true)
           .setContentIntent(intent).setPriority(Notification.PRIORITY_HIGH);
        manager.notify(notificationCounter++,builder.build());
    }

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.rgb(7,17,30));
        getWindow().setNavigationBarColor(Color.rgb(7,17,30));
        if (Build.VERSION.SDK_INT>=26) {
            NotificationManager nm=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
            if(nm!=null) nm.createNotificationChannel(new NotificationChannel(SOCIAL_CHANNEL,"Arkadaş ve maç davetleri",NotificationManager.IMPORTANCE_HIGH));
        }
        if (Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},1234);
        root = new FrameLayout(this);
        root.setBackgroundColor(Color.rgb(7,17,30));
        setContentView(root);

        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(7,17,30));
        root.addView(webView, new FrameLayout.LayoutParams(-1, -1));
        webView.getSettings().setJavaScriptEnabled(true);
        webView.addJavascriptInterface(new NativeBridge(),"AndroidBridge");
        webView.getSettings().setDomStorageEnabled(true);
        webView.getSettings().setAllowFileAccess(false);
        webView.getSettings().setAllowContentAccess(false);
        webView.getSettings().setJavaScriptCanOpenWindowsAutomatically(false);
        webView.getSettings().setMediaPlaybackRequiresUserGesture(true);
        webView.getSettings().setMixedContentMode(android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        if (Build.VERSION.SDK_INT >= 26) webView.getSettings().setSafeBrowsingEnabled(true);
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, false);

        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if ("https".equalsIgnoreCase(uri.getScheme()) && HOST.equalsIgnoreCase(uri.getHost())) return false;
                if ("https".equalsIgnoreCase(uri.getScheme()) || "mailto".equalsIgnoreCase(uri.getScheme())) {
                    try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); }
                    catch (Exception ignored) { Toast.makeText(MainActivity.this,"Bağlantı açılamadı.",Toast.LENGTH_SHORT).show(); }
                }
                return true;
            }
            @Override public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                loadingError = false;
                hideOffline();
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest request, android.webkit.WebResourceError error) {
                if (request.isForMainFrame()) {
                    loadingError = true;
                    showOffline();
                }
            }
            @Override public void onPageFinished(WebView view, String url) {
                if (loadingError || !hasNetwork()) showOffline();
                else hideOffline();
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onJsPrompt(WebView view, String url, String message, String defaultValue, JsPromptResult result) {
                // Native clipboard fallback for the game's invitation link.
                if (url.startsWith(HOME) && "Bağlantıyı kopyala:".equals(message)
                        && defaultValue != null && defaultValue.startsWith(HOME)) {
                    ClipboardManager clip = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                    clip.setPrimaryClip(ClipData.newPlainText("Ortak Futbolcu Davet", defaultValue));
                    Toast.makeText(MainActivity.this, "Davet bağlantısı kopyalandı", Toast.LENGTH_SHORT).show();
                    result.confirm(defaultValue);
                    return true;
                }
                return super.onJsPrompt(view,url,message,defaultValue,result);
            }
        });
        if (!hasNetwork()) showOffline();
        webView.loadUrl(HOME);
    }

    private boolean hasNetwork() {
        ConnectivityManager manager=(ConnectivityManager)getSystemService(CONNECTIVITY_SERVICE);
        if(manager == null || manager.getActiveNetwork() == null) return false;
        NetworkCapabilities nc=manager.getNetworkCapabilities(manager.getActiveNetwork());
        return nc != null && nc.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET);
    }

    private void showOffline() {
        if(offlineView != null) return;
        LinearLayout panel=new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setGravity(Gravity.CENTER);
        panel.setPadding(dp(32),dp(24),dp(32),dp(24));
        panel.setBackgroundColor(Color.rgb(7,17,30));
        TextView badge=new TextView(this);
        badge.setText("⚽"); badge.setGravity(Gravity.CENTER); badge.setTextSize(54);
        panel.addView(badge);
        TextView title=new TextView(this);
        title.setText("BAĞLANTI KURULAMADI"); title.setTextColor(Color.WHITE); title.setTextSize(21);
        title.setTypeface(Typeface.DEFAULT, Typeface.BOLD); title.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams tp=new LinearLayout.LayoutParams(-1,-2); tp.topMargin=dp(20);
        panel.addView(title,tp);
        TextView info=new TextView(this);
        info.setText("Oynamak için internet bağlantısı gerekiyor. Bağlantını kontrol edip yeniden dene.");
        info.setTextColor(Color.rgb(171,193,207)); info.setTextSize(15);info.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams ip=new LinearLayout.LayoutParams(-1,-2);ip.topMargin=dp(12);
        panel.addView(info,ip);
        Button retry=new Button(this);
        retry.setText("TEKRAR DENE");retry.setTextColor(Color.rgb(7,17,30));
        retry.setBackgroundTintList(android.content.res.ColorStateList.valueOf(Color.rgb(36,216,182)));
        LinearLayout.LayoutParams bp=new LinearLayout.LayoutParams(-1,dp(52));bp.topMargin=dp(28);
        panel.addView(retry,bp);
        retry.setOnClickListener(v->{ hideOffline(); webView.loadUrl(HOME); });
        offlineView=panel;
        root.addView(panel,new FrameLayout.LayoutParams(-1,-1));
    }

    private void hideOffline() {
        if(offlineView != null){root.removeView(offlineView);offlineView=null;}
    }

    private int dp(float d) { return (int)(d*getResources().getDisplayMetrics().density + 0.5f); }

    @Override public void onBackPressed() {
        if (webView == null) { super.onBackPressed(); return; }
        // Keep back handling inside the live SPA; never inadvertently leave a match.
        webView.evaluateJavascript("(function(){try{return typeof window.ortakBack==='function' ? window.ortakBack() : false;}catch(e){return false;}})()", value -> {
            if (!"true".equals(value)) new AlertDialog.Builder(this)
                .setTitle("Oyundan çıkılsın mı?")
                .setMessage("Ortak Futbolcu'dan çıkmak istediğine emin misin?")
                .setNegativeButton("Vazgeç",(d,w)->{})
                .setPositiveButton("Çıkış",(d,w)->finish())
                .show();
        });
    }

    @Override protected void onDestroy() {
        if(webView != null){
            root.removeView(webView);
            webView.stopLoading();
            webView.loadUrl("about:blank");
            webView.clearHistory();
            webView.destroy();
            webView=null;
        }
        super.onDestroy();
    }
}
