package com.example.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.data.CatalogRepository
import com.example.data.I18n
import com.example.model.TourStatus
import com.example.viewmodel.GloviUiState
import com.example.viewmodel.GloviViewModel

@Composable
fun RoutesScreen(
    state: GloviUiState,
    viewModel: GloviViewModel,
    modifier: Modifier = Modifier
) {
    val lang = state.profile.language
    val context = LocalContext.current
    val tour = state.tour
    val visitedCount = tour?.visited?.size ?: 0
    val totalCount = CatalogRepository.pois.size
    val isTourActive = tour?.status == TourStatus.ACTIVE

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 16.dp)
            .testTag("routes_screen")
    ) {
        Text(
            text = "${I18n.t("routes", lang)} · Ceuta",
            style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold)
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = I18n.t("routeHint", lang),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
        )

        Spacer(modifier = Modifier.height(16.dp))

        // Progress Card
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .testTag("progress_card"),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.primaryContainer
            )
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                val statusText = when (tour?.status) {
                    TourStatus.ACTIVE -> I18n.t("active", lang)
                    TourStatus.COMPLETED -> I18n.t("completed", lang)
                    TourStatus.ABANDONED -> I18n.t("abandoned", lang)
                    else -> "0 / 3"
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "$visitedCount / $totalCount · $statusText",
                        style = MaterialTheme.typography.titleMedium.copy(
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        ),
                        modifier = Modifier.testTag("text_progress")
                    )

                    if (state.isSpeaking) {
                        IconButton(
                            onClick = { viewModel.stopSpeaking() },
                            modifier = Modifier.testTag("btn_stop_speech")
                        ) {
                            Icon(
                                imageVector = Icons.Default.VolumeOff,
                                contentDescription = I18n.t("stopVoice", lang),
                                tint = MaterialTheme.colorScheme.error
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))
                LinearProgressIndicator(
                    progress = { if (totalCount > 0) visitedCount.toFloat() / totalCount else 0f },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(8.dp)
                        .clip(RoundedCornerShape(4.dp)),
                    color = MaterialTheme.colorScheme.primary,
                    trackColor = MaterialTheme.colorScheme.surface
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Actions: Iniciar / Abandonar / GPS / Simular
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            if (!isTourActive) {
                Button(
                    onClick = { viewModel.startTour() },
                    modifier = Modifier
                        .weight(1f)
                        .testTag("btn_start_tour"),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary
                    )
                ) {
                    Icon(Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(I18n.t("start", lang))
                }
            } else {
                OutlinedButton(
                    onClick = { viewModel.abandonTour() },
                    modifier = Modifier
                        .weight(1f)
                        .testTag("btn_abandon_tour")
                ) {
                    Icon(Icons.Default.Stop, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(I18n.t("abandon", lang))
                }
            }

            Button(
                onClick = {
                    if (state.isTrackingGps) viewModel.stopGpsTracking() else viewModel.startGpsTracking()
                },
                enabled = state.profile.locationConsent && isTourActive,
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (state.isTrackingGps) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.surfaceVariant,
                    contentColor = if (state.isTrackingGps) MaterialTheme.colorScheme.onSecondary else MaterialTheme.colorScheme.onSurfaceVariant
                ),
                modifier = Modifier
                    .weight(1f)
                    .testTag("btn_toggle_gps")
            ) {
                Icon(
                    imageVector = if (state.isTrackingGps) Icons.Default.LocationOn else Icons.Default.LocationOff,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(I18n.t(if (state.isTrackingGps) "stopGps" else "gps", lang))
            }
        }

        // Quick simulation helper when tour is active
        if (isTourActive) {
            Spacer(modifier = Modifier.height(12.dp))
            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text(
                        text = I18n.t("simulateArrival", lang) + " (GPS 100m):",
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        CatalogRepository.pois.forEach { poi ->
                            val isVisited = tour?.visited?.contains(poi.id) == true
                            FilledTonalButton(
                                onClick = { viewModel.simulateArrival(poi.id) },
                                enabled = !isVisited,
                                modifier = Modifier
                                    .weight(1f)
                                    .testTag("btn_simulate_${poi.id}"),
                                contentPadding = PaddingValues(horizontal = 4.dp, vertical = 6.dp)
                            ) {
                                Text(
                                    text = poi.name.split(" ").firstOrNull() ?: poi.name,
                                    style = MaterialTheme.typography.labelSmall
                                )
                            }
                        }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(20.dp))

        // POI Stops List
        Text(
            text = "Paradas del recorrido",
            style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold)
        )
        Spacer(modifier = Modifier.height(12.dp))

        CatalogRepository.pois.forEachIndexed { index, poi ->
            val isVisited = tour?.visited?.contains(poi.id) == true
            val narration = CatalogRepository.getLocalizedNarration(
                poi, lang, state.profile.interests
            )

            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 8.dp)
                    .testTag("card_poi_${poi.id}"),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(
                    containerColor = if (isVisited) MaterialTheme.colorScheme.surfaceVariant else MaterialTheme.colorScheme.surface
                ),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column {
                    val resId = context.resources.getIdentifier(poi.drawableResName, "drawable", context.packageName)
                    if (resId != 0) {
                        Image(
                            painter = painterResource(id = resId),
                            contentDescription = poi.name,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(160.dp),
                            contentScale = ContentScale.Crop
                        )
                    }

                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                text = "${index + 1}. ${poi.name}",
                                style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold)
                            )
                            if (isVisited) {
                                Surface(
                                    color = MaterialTheme.colorScheme.primary,
                                    shape = RoundedCornerShape(8.dp)
                                ) {
                                    Text(
                                        text = "✓ Visitado",
                                        color = MaterialTheme.colorScheme.onPrimary,
                                        style = MaterialTheme.typography.labelSmall,
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = narration,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.85f)
                        )

                        Spacer(modifier = Modifier.height(14.dp))

                        Row(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Button(
                                onClick = { viewModel.speakNarration(narration) },
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = MaterialTheme.colorScheme.primaryContainer,
                                    contentColor = MaterialTheme.colorScheme.onPrimaryContainer
                                ),
                                modifier = Modifier.testTag("btn_listen_${poi.id}")
                            ) {
                                Icon(Icons.Default.VolumeUp, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(I18n.t("listen", lang))
                            }

                            OutlinedButton(
                                onClick = {
                                    val gmmIntentUri = Uri.parse("geo:${poi.latitude},${poi.longitude}?q=${poi.latitude},${poi.longitude}(${poi.name})")
                                    val mapIntent = Intent(Intent.ACTION_VIEW, gmmIntentUri)
                                    context.startActivity(mapIntent)
                                },
                                modifier = Modifier.testTag("btn_navigate_${poi.id}")
                            ) {
                                Icon(Icons.Default.DirectionsWalk, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(I18n.t("navigate", lang))
                            }

                            IconButton(
                                onClick = {
                                    val browserIntent = Intent(Intent.ACTION_VIEW, Uri.parse(poi.source))
                                    context.startActivity(browserIntent)
                                },
                                modifier = Modifier.testTag("btn_source_${poi.id}")
                            ) {
                                Icon(Icons.Default.OpenInNew, contentDescription = I18n.t("source", lang))
                            }
                        }
                    }
                }
            }
        }
    }
}
