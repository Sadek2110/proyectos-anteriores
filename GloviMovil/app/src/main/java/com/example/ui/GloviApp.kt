package com.example.ui

import android.content.Intent
import android.net.Uri
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.I18n
import com.example.model.Language
import com.example.ui.screens.*
import com.example.viewmodel.AppSection
import com.example.viewmodel.GloviUiState
import com.example.viewmodel.GloviViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GloviApp(
    viewModel: GloviViewModel,
    modifier: Modifier = Modifier
) {
    val state by viewModel.uiState.collectAsState()
    val lang = state.profile.language
    val context = LocalContext.current

    // Handle system back navigation: return to HOME if in another tab
    if (state.section != AppSection.HOME) {
        BackHandler {
            viewModel.selectSection(AppSection.HOME)
        }
    }

    Scaffold(
        topBar = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.background)
                    .statusBarsPadding()
                    .padding(horizontal = 16.dp, vertical = 8.dp)
            ) {
                // Top micro-bar: Subtitle, Language dropdown, SOS 112 button
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = I18n.t("intro", lang),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.7f)
                    )

                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        // Language Dropdown
                        var langMenuExpanded by remember { mutableStateOf(false) }
                        Box {
                            Surface(
                                shape = RoundedCornerShape(8.dp),
                                color = MaterialTheme.colorScheme.surface,
                                shadowElevation = 1.dp,
                                modifier = Modifier
                                    .clickable { langMenuExpanded = true }
                                    .testTag("btn_language_selector")
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Language,
                                        contentDescription = null,
                                        modifier = Modifier.size(14.dp),
                                        tint = MaterialTheme.colorScheme.primary
                                    )
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text(
                                        text = lang.displayName,
                                        style = MaterialTheme.typography.labelSmall
                                    )
                                }
                            }

                            DropdownMenu(
                                expanded = langMenuExpanded,
                                onDismissRequest = { langMenuExpanded = false }
                            ) {
                                Language.entries.forEach { l ->
                                    DropdownMenuItem(
                                        text = { Text(l.displayName) },
                                        onClick = {
                                            viewModel.updateLanguage(l)
                                            langMenuExpanded = false
                                        }
                                    )
                                }
                            }
                        }

                        // SOS Button
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = MaterialTheme.colorScheme.error,
                            modifier = Modifier
                                .clickable {
                                    val dialIntent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:112"))
                                    context.startActivity(dialIntent)
                                }
                                .testTag("btn_sos_call_header")
                        ) {
                            Text(
                                text = "SOS 112",
                                color = Color.White,
                                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(4.dp))

                // Wordmark: GLOVI · Ceuta
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.Bottom
                ) {
                    Row(verticalAlignment = Alignment.Bottom) {
                        Text(
                            text = "GLOVI",
                            style = MaterialTheme.typography.headlineLarge.copy(
                                fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Serif,
                                color = MaterialTheme.colorScheme.primary,
                                letterSpacing = 1.sp
                            )
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "Ceuta",
                            style = MaterialTheme.typography.titleMedium.copy(
                                color = MaterialTheme.colorScheme.secondary,
                                fontWeight = FontWeight.Medium
                            ),
                            modifier = Modifier.padding(bottom = 4.dp)
                        )
                    }

                    // Admin shortcut icon
                    IconButton(
                        onClick = { viewModel.selectSection(AppSection.ADMIN) },
                        modifier = Modifier.testTag("btn_admin_portal")
                    ) {
                        Icon(
                            imageVector = Icons.Default.AdminPanelSettings,
                            contentDescription = "Operación",
                            tint = if (state.section == AppSection.ADMIN) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onBackground.copy(alpha = 0.5f)
                        )
                    }
                }

                state.noticeMessage?.let { notice ->
                    Spacer(modifier = Modifier.height(6.dp))
                    Surface(
                        color = MaterialTheme.colorScheme.primaryContainer,
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = notice,
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onPrimaryContainer,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)
                        )
                    }
                }
            }
        },
        bottomBar = {
            NavigationBar(
                containerColor = MaterialTheme.colorScheme.surface,
                tonalElevation = 8.dp
            ) {
                val navItems = listOf(
                    Triple(AppSection.HOME, Icons.Default.Home, "home"),
                    Triple(AppSection.ROUTES, Icons.Default.Explore, "routes"),
                    Triple(AppSection.ASSISTANT, Icons.Default.AutoAwesome, "nav_assistant"),
                    Triple(AppSection.BOOKINGS, Icons.Default.CalendarToday, "nav_bookings"),
                    Triple(AppSection.EMERGENCY, Icons.Default.Warning, "nav_emergency"),
                    Triple(AppSection.PRIVACY, Icons.Default.Lock, "nav_privacy")
                )

                navItems.forEach { (section, icon, labelKey) ->
                    val isSelected = state.section == section
                    NavigationBarItem(
                        selected = isSelected,
                        onClick = { viewModel.selectSection(section) },
                        icon = { Icon(icon, contentDescription = I18n.t(labelKey, lang)) },
                        label = { Text(I18n.t(labelKey, lang), maxLines = 1, overflow = TextOverflow.Ellipsis) },
                        modifier = Modifier.testTag("nav_tab_${section.id}")
                    )
                }
            }
        },
        modifier = modifier
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(MaterialTheme.colorScheme.background)
        ) {
            when (state.section) {
                AppSection.HOME -> HomeScreen(
                    state = state,
                    viewModel = viewModel,
                    onNavigate = { viewModel.selectSection(it) }
                )
                AppSection.ROUTES -> RoutesScreen(
                    state = state,
                    viewModel = viewModel
                )
                AppSection.ASSISTANT -> AssistantScreen(
                    state = state,
                    viewModel = viewModel
                )
                AppSection.BOOKINGS -> BookingsScreen(
                    state = state,
                    viewModel = viewModel
                )
                AppSection.EMERGENCY -> EmergencyScreen(
                    state = state
                )
                AppSection.PRIVACY -> PrivacyScreen(
                    state = state,
                    viewModel = viewModel
                )
                AppSection.ADMIN -> AdminScreen(
                    state = state,
                    viewModel = viewModel
                )
            }
        }
    }
}
