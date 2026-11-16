package com.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import com.example.ui.GloviApp
import com.example.ui.theme.GloviTheme
import com.example.viewmodel.GloviViewModel

class MainActivity : ComponentActivity() {

    private val viewModel: GloviViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            GloviTheme {
                GloviApp(viewModel = viewModel)
            }
        }
    }
}
