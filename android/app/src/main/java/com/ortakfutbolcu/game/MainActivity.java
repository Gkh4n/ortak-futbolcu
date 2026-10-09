package com.ortakfutbolcu.game;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.ConnectivityManager;
import android.net.NetworkCapabilities;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.JsPromptResult;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity extends Activity {
  private static final String HOME = "https://ortak-futbolcu.onrender.com/";
  private static final String HOST = "ortak-futbolcu.onrender.com";
  private WebView webView;
  private FrameLayout root;
  private View offline;
  private boolean pageError;

  @Override public void onCreate(Bundle state) {
    super.onCreate(state);
    getWindow().setStatusBarColor(Color.rgb(7,17,30));
    getWindow().setNavigationBarColor(Color.rgb(7,17,30));
    root = new FrameLayout(this);
    root.setBackgroundColor(Color.rgb(7,17,30));
    setContentView(root);
    webView = new WebView(this);
    webView.setBackgroundColor(Color.rgb(7,17,30));
    root.addView(webView, new FrameLayout.LayoutParams(-1,-1));
    webView.getSettings().setJavaScriptEnabled(true);
    webView.getSettings().setDomStorageEnabled(true);
    webView.getSettings().setAllowFileAccess(false);
    webView.getSettings().setAllowContentAccess(false);
    webView.getSettings().setJavaScriptCanOpenWindowsAutomatically(false);
    webView.getSettings().setMixedContentMode(android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW);
    if (Build.VERSION.SDK_INT>=26) webView.getSettings().setSafeBrowsingEnabled(true);
    CookieManager.getInstance().setAcceptCookie(true);
    CookieManager.getInstance().setAcceptThirdPartyCookies(webView, false);
    webView.setWebViewClient(new WebViewClient(){
      @Override public boolean shouldOverrideUrlLoading(WebView w, WebResourceRequest request) {
        Uri url=request.getUrl();
        if ("https".equalsIgnoreCase(url.getScheme()) && HOST.equalsIgnoreCase(url.getHost())) return false;
        if ("https".equalsIgnoreCase(url.getScheme()) || "mailto".equalsIgnoreCase(url.getScheme())) {
          try { startActivity(new Intent(Intent.ACTION_VIEW,url)); }
          catch(Exception e){Toast.makeText(MainActivity.this,"Bağlantı açılamadı",Toast.LENGTH_SHORT).show();}
        }
        return true;
      }
      @Override public void onPageStarted(WebView w,String url,android.graphics.Bitmap icon){pageError=false;hideOffline();}
      @Override public void onReceivedError(WebView w,WebResourceRequest request,android.webkit.WebResourceError err) {
        if(request.isForMainFrame()){pageError=true;showOffline();}
      }
      @Override public void onPageFinished(WebView w,String url) {
        if(pageError || !online()) showOffline(); else hideOffline();
      }
    });
    webView.setWebChromeClient(new WebChromeClient(){
      @Override public boolean onJsPrompt(WebView w,String url,String message,String value,JsPromptResult result) {
        if(url.startsWith(HOME) && "Bağlantıyı kopyala:".equals(message) && value!=null && value.startsWith(HOME)){
          ClipboardManager clipboard=(ClipboardManager)getSystemService(Context.CLIPBOARD_SERVICE);
          clipboard.setPrimaryClip(ClipData.newPlainText("Davet",value));
          Toast.makeText(MainActivity.this,"Davet bağlantısı kopyalandı",Toast.LENGTH_SHORT).show();
          result.confirm(value);
          return true;
        }
        return super.onJsPrompt(w,url,message,value,result);
      }
    });
    if(!online())showOffline();
    webView.loadUrl(HOME);
  }

  private boolean online(){
    ConnectivityManager c=(ConnectivityManager)getSystemService(CONNECTIVITY_SERVICE);
    if(c==null || c.getActiveNetwork()==null) return false;
    NetworkCapabilities n=c.getNetworkCapabilities(c.getActiveNetwork());
    return n!=null && n.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET);
  }
  private int dp(int n){return (int)(n*getResources().getDisplayMetrics().density+0.5f);}
  private void showOffline(){
    if(offline!=null) return;
    LinearLayout p=new LinearLayout(this);
    p.setOrientation(LinearLayout.VERTICAL);
    p.setGravity(Gravity.CENTER);
    p.setPadding(dp(24),dp(24),dp(24),dp(24));
    p.setBackgroundColor(Color.rgb(7,17,30));
    TextView title=new TextView(this);
    title.setText("BAĞLANTI KURULAMADI");
    title.setTextColor(Color.WHITE);title.setTextSize(21);
    title.setGravity(Gravity.CENTER);title.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
    p.addView(title);
    TextView text=new TextView(this);
    text.setText("Oyuna bağlanmak için internet gerekiyor. Bağlantını kontrol edip tekrar dene.");
    text.setTextColor(Color.rgb(171,193,207));
    text.setTextSize(15);text.setGravity(Gravity.CENTER);
    LinearLayout.LayoutParams info=new LinearLayout.LayoutParams(-1,-2);info.topMargin=dp(16);
    p.addView(text,info);
    Button retry=new Button(this);
    retry.setText("TEKRAR DENE");
    retry.setTextColor(Color.rgb(7,17,30));
    retry.setBackgroundTintList(ColorStateList.valueOf(Color.rgb(36,216,182)));
    LinearLayout.LayoutParams bp=new LinearLayout.LayoutParams(-1,dp(54));bp.topMargin=dp(25);
    p.addView(retry,bp);
    retry.setOnClickListener(v->{hideOffline();webView.loadUrl(HOME);});
    offline=p;root.addView(offline,new FrameLayout.LayoutParams(-1,-1));
  }
  private void hideOffline(){if(offline!=null){root.removeView(offline);offline=null;}}
  @Override public void onBackPressed(){
    if(webView.canGoBack()){webView.goBack();return;}
    webView.evaluateJavascript("(function(){try{if(typeof app!=='undefined'&&app.mode!=='home'&&app.mode!=='auth'){document.querySelector('[data-action=home]').click();return true;}return false;}catch(e){return false;}})()", value->{
      if(!"true".equals(value)) new AlertDialog.Builder(this)
        .setTitle("Oyundan çıkılsın mı?")
        .setMessage("Ortak Futbolcu'dan çıkmak istediğine emin misin?")
        .setNegativeButton("Vazgeç",(d,w)->{})
        .setPositiveButton("Çıkış",(d,w)->finish()).show();
    });
  }
  @Override protected void onDestroy(){
    if(webView!=null){root.removeView(webView);webView.stopLoading();webView.loadUrl("about:blank");webView.destroy();webView=null;}
    super.onDestroy();
  }
}
